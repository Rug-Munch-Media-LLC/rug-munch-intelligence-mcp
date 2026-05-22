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
    """Parse RMI_TOOLS definitions from a gateway index.ts file"""
    index_path = os.path.join(gateway_dir, "index.ts")
    if not os.path.exists(index_path):
        return []
    
    with open(index_path, 'r') as f:
        content = f.read()
    
    # Extract tool definitions using regex
    tools = []
    pattern = r'(\w+):\s*\{\s*name:\s*"([^"]+)",\s*description:\s*"([^"]+)",\s*price:\s*"\$([^"]+)",\s*priceAtomic:\s*"([^"]+)",\s*category:\s*"([^"]+)",\s*trialFree:\s*(\d+),\s*method:\s*"([^"]+)"'
    
    for match in re.finditer(pattern, content):
        tool_id, name, desc, price, atomic, category, trial, method = match.groups()
        tools.append({
            "id": tool_id,
            "name": name,
            "description": desc,
            "price": f"${price}",
            "priceUsd": float(price),
            "category": category.lower(),
            "trialFree": int(trial),
            "method": method,
            "service": "rmi-native",
            "source": "native",
        })
    
    return tools


def load_external_mcp_tools() -> List[Dict]:
    """Load expanded external MCP tool definitions"""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    catalog_path = os.path.join(base_dir, "services", "expanded_mcp_catalog.py")
    if not os.path.exists(catalog_path):
        return []
    
    try:
        # Read and exec to get EXTERNAL_MCP_TOOLS
        import importlib.util
        spec = importlib.util.spec_from_file_location("expanded_mcp_catalog", catalog_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "EXTERNAL_MCP_TOOLS", [])
    except Exception as e:
        logger.error(f"Failed to load external MCP catalog: {e}")
        return []


def get_catalog():
    """Build full tool catalog from all gateways + external MCP servers"""
    # Always rebuild (no stale caching)
    gateway_base = "/srv/rmi/backend/x402-gateway"
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