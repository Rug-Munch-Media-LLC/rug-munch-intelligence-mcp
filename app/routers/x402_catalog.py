"""Dynamic MCP Tool Catalog — reads from gateway configs + external MCP servers
Expanded to include 200+ tools across 40+ services
"""
import os
import json
import re
import logging
from typing import List, Dict
from fastapi import APIRouter

logger = logging.getLogger(__name__)

# Provider name sanitization map
_PROVIDER_MAP = {
    "DexScreener": "DEX",
    "CoinGecko": "Market Data",
    "DefiLlama": "DeFi Analytics",
    "Birdeye": "Token Discovery",
    "PumpFun": "Launch",
    "Pump.fun": "Launch",
    "GeckoTerminal": "DEX Pool",
    "DexPaprika": "Multi-Source DEX",
}

_SERVICE_MAP = {
    "dexscreener": "dex-analytics",
    "coingecko": "market-data",
    "defillama": "defi-analytics",
    "birdeye": "token-discovery",
    "pumpfun": "launch-platform",
    "geckoterminal": "dex-pool-data",
    "dexpaprika": "multi-source-dex",
    "dexscreener_new": "dex-analytics",
    "dexscreener_hot": "dex-analytics",
    "dexscreener_meme": "dex-analytics",
    "defillama_stablecoins": "defi-analytics",
    "defillama_bridges": "defi-analytics",
    "pumpfun_gainers": "launch-platform",
}


def _sanitize_tool(tool: dict) -> dict:
    """Remove upstream provider names from user-visible tool fields"""
    for field in ("name", "description"):
        if field in tool and isinstance(tool[field], str):
            val = tool[field]
            for old, new in _PROVIDER_MAP.items():
                val = val.replace(old, new)
            tool[field] = val
    if "service" in tool and isinstance(tool["service"], str):
        tool["service"] = _SERVICE_MAP.get(tool["service"], tool["service"])
    return tool


router = APIRouter(prefix="/api/v1/x402", tags=["x402-catalog"])

# Cache for tool catalog
_catalog_cache: Dict = {}


def parse_gateway_tools(gateway_dir: str) -> List[Dict]:
    """Parse RMI_TOOLS definitions from a gateway index.ts file.
    
    Handles nested braces by tracking brace depth."""
    index_path = os.path.join(gateway_dir, "index.ts")
    if not os.path.exists(index_path):
        return []
    
    with open(index_path, 'r') as f:
        content = f.read()
    
    tools = []
    
    # Find the RMI_TOOLS block
    rmi_start = content.find("const RMI_TOOLS")
    if rmi_start == -1:
        return []
    
    # Find opening brace of RMI_TOOLS
    brace_start = content.find("{", rmi_start)
    if brace_start == -1:
        return []
    
    # Find matching closing brace by tracking depth
    depth = 0
    pos = brace_start
    while pos < len(content):
        if content[pos] == '{':
            depth += 1
        elif content[pos] == '}':
            depth -= 1
            if depth == 0:
                break
        pos += 1
    
    rmi_block = content[brace_start:pos+1]
    
    # Now parse individual tool definitions within the block
    # Tools look like:  tool_name: { name: "...", description: "...", ... }
    # We need to handle nested braces in extras
    
    # Split into tool entries by finding top-level 'word:' patterns
    tool_pattern = re.compile(r'(\w+):\s*\{', re.MULTILINE)
    
    for tm in tool_pattern.finditer(rmi_block):
        tool_id = tm.group(1)
        
        # Skip non-tool entries
        if tool_id in ('interface', 'type', 'export', 'import', 'const', 'let', 'var'):
            continue
        if tool_id.startswith('//') or tool_id.startswith('RMI_TOOLS'):
            continue
        
        # Find the matching closing brace for this tool
        tool_start = tm.end() - 1  # position of opening {
        depth = 0
        tool_end = tool_start
        for i in range(tool_start, len(rmi_block)):
            if rmi_block[i] == '{':
                depth += 1
            elif rmi_block[i] == '}':
                depth -= 1
                if depth == 0:
                    tool_end = i + 1
                    break
        
        block = rmi_block[tool_start:tool_end]
        
        # Extract fields
        name = re.search(r'name:\s*"([^"]*)"', block)
        desc = re.search(r'description:\s*"([^"]*)"', block)
        price = re.search(r'price:\s*"\$?([^"]*)"', block)
        atomic = re.search(r'priceAtomic:\s*"([^"]*)"', block)
        category = re.search(r'category:\s*"([^"]*)"', block)
        trial = re.search(r'trialFree:\s*(\d+)', block)
        method = re.search(r'method:\s*"([^"]*)"', block)
        
        if name and category:
            tools.append({
                "id": tool_id,
                "name": name.group(1),
                "description": desc.group(1) if desc else "",
                "price": f"${price.group(1)}" if price else "$0",
                "priceUsd": float(price.group(1)) if price else 0,
                "priceAtomic": atomic.group(1) if atomic else "0",
                "category": category.group(1).lower(),
                "trialFree": int(trial.group(1)) if trial else 0,
                "method": method.group(1) if method else "POST",
                "service": "rmi-native",
                "source": "native",
            })
    
    return tools


def load_external_mcp_tools() -> List[Dict]:
    """Load expanded external MCP tool definitions.
    
    Priority:
    1. Local expanded_mcp_catalog.py file (fast, offline)
    2. mcp-router.rugmunch.io/tools (live, always current)
    3. Returns empty list if both unavailable
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    catalog_path = os.path.join(base_dir, "services", "expanded_mcp_catalog.py")
    
    # Try local file first
    if os.path.exists(catalog_path):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("expanded_mcp_catalog", catalog_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            tools = getattr(module, "EXTERNAL_MCP_TOOLS", [])
            if tools:
                logger.info(f"Loaded {len(tools)} tools from expanded_mcp_catalog.py")
                return tools
        except Exception as e:
            logger.warning(f"Failed to load expanded_mcp_catalog.py: {e}")
    
    # Fallback: fetch from mcp-router dynamically
    try:
        import urllib.request, json as _json
        url = "https://mcp-router.rugmunch.io/tools"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read())
        
        tools = []
        # mcp-router returns service groups, each with tools
        if isinstance(data, dict):
            services = data.get("services", data.get("tools", data))
            if isinstance(services, list):
                for service in services:
                    service_name = service.get("name", service.get("service", "unknown"))
                    service_tools = service.get("tools", [])
                    if isinstance(service_tools, list):
                        for t in service_tools:
                            tool_id = t.get("name", t.get("id", ""))
                            if tool_id:
                                tools.append({
                                    "id": tool_id,
                                    "name": t.get("description", tool_id),
                                    "description": t.get("description", f"MCP tool: {tool_id}"),
                                    "price": "$0.01",
                                    "priceUsd": 0.01,
                                    "category": "mcp-external",
                                    "trialFree": 3,
                                    "method": "MCP",
                                    "service": service_name,
                                    "source": "mcp-router",
                                    "chains": ["SOLANA", "BASE"],
                                })
                    else:
                        # Flat tool list
                        for key, val in service.items():
                            if isinstance(val, dict) and "name" in val:
                                tools.append({
                                    "id": key,
                                    "name": val.get("name", key),
                                    "description": val.get("description", ""),
                                    "price": "$0.01",
                                    "priceUsd": 0.01,
                                    "category": "mcp-external",
                                    "trialFree": 3,
                                    "method": "MCP",
                                    "service": service_name,
                                    "source": "mcp-router",
                                    "chains": ["SOLANA", "BASE"],
                                })
        
        if tools:
            logger.info(f"Loaded {len(tools)} tools from mcp-router dynamically")
            return tools
    except Exception as e:
        logger.warning(f"Failed to fetch from mcp-router: {e}")
    
    return []


def discover_route_tools() -> List[Dict]:
    """Discover tools from FastAPI route definitions"""
    tools = []
    backend_dir = os.path.dirname(__file__)
    skip = {'bundles', 'discovery', 'frameworks', 'comprehensive_audit',
            'anthropic-tools', 'gemini-tools', 'langchain-tools', 'openai-tools',
            'bundles/all_in_one', 'bundles/intelligence_pack', 'bundles/security_pack'}
    
    for fname in ["x402_tools.py", "x402_forensic_tools.py"]:
        fpath = os.path.join(backend_dir, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f:
            content = f.read()
        # Find all route paths
        routes = re.findall(r'@router\.(?:get|post)\("/([^"]+)"\)', content)
        for route in routes:
            if route in skip:
                continue
            # Try to find docstring for description
            desc = f"Tool: {route}"
            doc_match = re.search(rf'@router\.(?:get|post)\("/{route}"\)[\s\S]*?"""([^"]*)"""', content)
            if doc_match:
                desc = doc_match.group(1).strip().split('\n')[0].strip()
            tools.append({
                "id": route, "name": route.replace('_', ' ').title(),
                "description": desc,
                "price": "$0.01", "priceUsd": 0.01, "category": "api",
                "trialFree": 1, "method": "POST",
                "service": "rmi-native", "source": "route", "chains": [],
            })
    return tools


def get_catalog():
    """Build full tool catalog from all gateways + external MCP servers"""
    # Always rebuild (no stale caching)
    base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    
    # Auto-detect gateway path (Docker: /app/x402-gateway, Local: /root/backend/x402-gateway)
    candidates = [
        "/app/x402-gateway",                                    # Docker
        os.path.join(base_dir, "x402-gateway"),                 # sibling of app/
        os.path.join(os.path.dirname(base_dir), "x402-gateway"),# parent of app/
        "/root/backend/x402-gateway",                           # canonical local
    ]
    gateway_base = None
    for c in candidates:
        if os.path.isdir(c):
            gateway_base = c
            break
    
    if not gateway_base:
        logger.warning("No x402-gateway directory found")
        gateway_base = "/app/x402-gateway"  # fallback for Docker
    chains = {}
    all_tools = {}  # Dedup by tool id
    services = set()
    categories = set()
    
    # Parse gateway tools (RMI native)
    if os.path.exists(gateway_base):
        for chain_dir in sorted(os.listdir(gateway_base)):
            chain_path = os.path.join(gateway_base, chain_dir)
            if not os.path.isdir(chain_path):
                continue
            
            tools = parse_gateway_tools(chain_path)
            if tools:
                chains[chain_dir] = len(tools)
                for t in tools:
                    if t["id"] not in all_tools:
                        t["chains"] = [chain_dir.upper()]
                        all_tools[t["id"]] = t
                    else:
                        if chain_dir.upper() not in all_tools[t["id"]]["chains"]:
                            all_tools[t["id"]]["chains"].append(chain_dir.upper())
                    services.add("rmi-native")
                    categories.add(t["category"])
    
    # Discover tools from FastAPI route definitions
    route_tools = discover_route_tools()
    for t in route_tools:
        if t["id"] not in all_tools:
            all_tools[t["id"]] = t
            services.add("rmi-native")
            categories.add(t["category"])
    
    # Load external MCP tools
    external_tools = load_external_mcp_tools()
    for t in external_tools:
        if t["id"] not in all_tools:
            t["chains"] = [c.upper() for c in t.get("chains", [])]
            all_tools[t["id"]] = t
            services.add(t.get("service", "unknown"))
            categories.add(t.get("category", "unknown"))
    
    # Sanitize ALL tools before returning
    tool_list = sorted([_sanitize_tool(dict(t)) for t in all_tools.values()], key=lambda x: x.get("priceUsd", 0))
    
    result = {
        "chains": chains,
        "total_tools": len(tool_list),
        "total_chains": len(chains),
        "total_services": len(services),
        "tools": tool_list,
        "categories": sorted(categories),
        "services": sorted(services),
    }
    
    _catalog_cache.clear()
    _catalog_cache.update(result)
    return result


@router.get("/tools-catalog")
async def list_tools_catalog():
    """Get all available MCP tools across all chains and external services"""
    return get_catalog()


@router.get("/tools-catalog/{chain}")
async def list_chain_tools(chain: str):
    """Get tools for a specific chain (includes native + external)"""
    catalog = get_catalog()
    chain_upper = chain.upper()
    chain_tools = [t for t in catalog["tools"] if chain_upper in t.get("chains", [])]
    return {"chain": chain, "count": len(chain_tools), "tools": chain_tools}


@router.get("/tools-catalog/category/{category}")
async def list_category_tools(category: str):
    """Get tools in a specific category across all chains"""
    catalog = get_catalog()
    filtered = [t for t in catalog["tools"] if t.get("category", "") == category.lower()]
    return {"category": category, "count": len(filtered), "tools": filtered}


@router.get("/tools-catalog/service/{service}")
async def list_service_tools(service: str):
    """Get tools from a specific external MCP service"""
    catalog = get_catalog()
    filtered = [t for t in catalog["tools"] if t.get("service", "") == service.lower()]
    return {"service": service, "count": len(filtered), "tools": filtered}