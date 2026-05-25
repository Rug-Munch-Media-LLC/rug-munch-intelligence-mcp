"""
SENTINEL — Multi-Chain Registry & Configuration
================================================
Centralized chain definitions, RPC endpoints, explorer APIs,
and data source configurations for all 13 supported chains.

Chains: solana, ethereum, base, bsc, arbitrum, polygon, avalanche,
        optimism, fantom, linea, zksync, scroll, mantle
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class ChainFamily(Enum):
    """Blockchain family classification."""
    SOLANA = "solana"       # Solana SPL tokens
    EVM = "evm"             # Ethereum Virtual Machine chains
    COSMOS = "cosmos"       # Not yet supported


@dataclass
class ChainConfig:
    """Full configuration for a supported blockchain."""
    name: str                       # Short name (e.g. "ethereum", "base")
    chain_id: str                   # Chain ID ("1", "8453", "solana")
    family: ChainFamily = ChainFamily.EVM
    display_name: str = ""          # Human name ("Ethereum", "Base")
    
    # RPC endpoints (primary, fallback, public)
    rpc_endpoints: List[str] = field(default_factory=list)
    
    # Block explorer API
    explorer_url: str = ""
    explorer_api_url: str = ""
    explorer_api_key_env: str = ""  # Env var for API key
    
    # Native token
    native_token_symbol: str = "ETH"
    native_token_decimals: int = 18
    
    # DEX data sources (DexScreener supports all)
    dexscreener_chain_id: str = ""  # Chain ID as DexScreener knows it
    
    # Known lockers / factory addresses
    known_lockers: Dict[str, str] = field(default_factory=dict)
    
    # CEX hot wallets for this chain
    cex_hot_wallets: Dict[str, List[str]] = field(default_factory=dict)
    
    # Block explorer API key env var
    api_key_env: str = ""
    
    def get_explorer_api_key(self) -> str:
        """Get the block explorer API key from environment."""
        return os.getenv(self.api_key_env, "")
    
    @property
    def is_solana(self) -> bool:
        return self.family == ChainFamily.SOLANA
    
    @property
    def is_evm(self) -> bool:
        return self.family == ChainFamily.EVM


# ─── Chain Registry ────────────────────────────────────────────────

CHAINS: Dict[str, ChainConfig] = {
    "solana": ChainConfig(
        name="solana",
        chain_id="solana",
        family=ChainFamily.SOLANA,
        display_name="Solana",
        rpc_endpoints=[
            "https://solana-mainnet.g.alchemy.com/v2/${ALCHEMY_KEY}",
            "https://mainnet.helius-rpc.com/?api-key=${HELIUS_API_KEY}",
            "https://solana.drpc.org",
            "https://solana-rpc.publicnode.com",
            "https://rpc.ankr.com/solana",
        ],
        explorer_url="https://solscan.io",
        explorer_api_url="https://public-api.solscan.io",
        explorer_api_key_env="SOLSCAN_API_KEY",
        native_token_symbol="SOL",
        native_token_decimals=9,
        dexscreener_chain_id="solana",
        known_lockers={},
        cex_hot_wallets={
            "Binance": [
                "5tzF4VG5DB9R4PJJZdE3EGX6MHcY7K6uAcAFN7b7zoyF",
                "DRpbCBMxVnDK7maPM4Gqt5iQJ3U1QorZ3Nz8g7Aeu9p",
                "9WzDXMPQefAPQgxPaMkr2Fi8nY91fMjJY4kMN7AhN2qh",
            ],
            "Coinbase": ["2AQ7xRF2Jq5k2C8RNqiP95jRskQk91nR6Nj4Q5xqG3x7"],
            "OKX": ["5YK5YK5YK5YK5YK5YK5YK5YK5YK5YK5YK5YK5YK5YK5Y"],
        },
        api_key_env="",
    ),
    
    "ethereum": ChainConfig(
        name="ethereum",
        chain_id="1",
        family=ChainFamily.EVM,
        display_name="Ethereum",
        rpc_endpoints=[
            "https://eth-mainnet.g.alchemy.com/v2/${ALCHEMY_KEY}",
            "https://ethereum-rpc.publicnode.com",
            "https://eth.llamarpc.com",
            "https://rpc.ankr.com/eth",
            "https://cloudflare-eth.com",
        ],
        explorer_url="https://etherscan.io",
        explorer_api_url="https://api.etherscan.io/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        native_token_symbol="ETH",
        native_token_decimals=18,
        dexscreener_chain_id="ethereum",
        known_lockers={
            "0x663A5C229c09b049E36dCc11a9B0d4a8c9c3dBC2": "UNCX Network",
            "0xe2fE530C047f2d85298b07D9333C05737f1435fB": "Team Finance",
            "0x7ee058420e5937496f5a2096f04caa7721cf70cc": "PinkLock",
        },
        cex_hot_wallets={
            "Binance": ["0x28C6c06298d514Db089934071355E5743bf21d60"],
            "Coinbase": ["0x503828976D22510aad0201ac7EC88293211D23Da"],
            "OKX": ["0x6cC5F688a315f3dC28A7781717a9A798a59fDA7b"],
            "Bybit": ["0xf89d7b9c864f589bbF53a82105107622B35EaA40"],
            "Kraken": ["0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2"],
            "KuCoin": ["0x2B5634C42055806a59e9107ED44D43c426E58258"],
            "Gate.io": ["0x0D0707963952f2fBA59dD06f2b425ace40b492Fe"],
            "Bitfinex": ["0x876EabF441B2EE5B5b0554Fd502a8E0600950cFa"],
            "Bitget": ["0x0639556F03714A74a5fEEaF5736a4A64f70Df206"],
            "MEXC": ["0x75e89d5979E4f6Fba9F97c104c2F0AFB3F1dcB88"],
            "HTX": ["0xeB2d2F1b8c558a40207669291Fda468E50c8a0Bb"],
            "OKEx": ["0x6cC5F688a315f3dC28A7781717a9A798a59fDA7b"],
            "Crypto.com": ["0x6262998Ced04146fA42253a5C0AF90CA02dfd2A3"],
            "Gemini": ["0xd24400ae8BfEBb18cA49Be86258a3C749cf46853"],
            "Korbit": ["0xF977814e90dA44bFA03b6295A0616a897441aceC"],
            "Bittrex": ["0x94b1B6eB67A7D14b2ad2Ee93FeBA5457c5451eF2"],
            "Bitstamp": ["0x00bdb5699745f5b860228c8f939abF1b9Ae374eD"],
        },
        api_key_env="ETHERSCAN_API_KEY",
    ),
    
    "base": ChainConfig(
        name="base",
        chain_id="8453",
        family=ChainFamily.EVM,
        display_name="Base",
        rpc_endpoints=[
            "https://base-mainnet.g.alchemy.com/v2/${ALCHEMY_KEY}",
            "https://mainnet.base.org",
            "https://base-rpc.publicnode.com",
            "https://rpc.ankr.com/base",
        ],
        explorer_url="https://basescan.org",
        explorer_api_url="https://api.basescan.org/api",
        explorer_api_key_env="BASESCAN_API_KEY",
        native_token_symbol="ETH",
        native_token_decimals=18,
        dexscreener_chain_id="base",
        known_lockers={
            "0x663A5C229c09b049E36dCc11a9B0d4a8c9c3dBC2": "UNCX Network",
            "0x7ee058420e5937496f5a2096f04caa7721cf70cc": "PinkLock",
        },
        cex_hot_wallets={
            "Coinbase": ["0x3304E22DDaa22bCdC5fCa2269b418046aE7b566A"],
        },
        api_key_env="BASESCAN_API_KEY",
    ),
    
    "bsc": ChainConfig(
        name="bsc",
        chain_id="56",
        family=ChainFamily.EVM,
        display_name="BSC",
        rpc_endpoints=[
            "https://bsc-dataseed.binance.org",
            "https://rpc.ankr.com/bsc",
            "https://bsc-rpc.publicnode.com",
            "https://bsc-mainnet.g.alchemy.com/v2/${ALCHEMY_KEY}",
        ],
        explorer_url="https://bscscan.com",
        explorer_api_url="https://api.bscscan.com/api",
        explorer_api_key_env="BSCSCAN_API_KEY",
        native_token_symbol="BNB",
        native_token_decimals=18,
        dexscreener_chain_id="bsc",
        known_lockers={
            "0x663A5C229c09b049E36dCc11a9B0d4a8c9c3dBC2": "UNCX Network",
            "0x7ee058420e5937496f5a2096f04caa7721cf70cc": "PinkLock",
            "0x2D8E3580C6E428d4EaA069198D0B76ae0f98e43a": "Mudra",
        },
        cex_hot_wallets={
            "Binance": ["0xB38e8c17e38363aF6EbdCb3dAE12e0243582891D"],
            "MEXC": ["0x51e6D27FA57373d8d4C256231241053a70Cb1d93"],
        },
        api_key_env="BSCSCAN_API_KEY",
    ),
    
    "arbitrum": ChainConfig(
        name="arbitrum",
        chain_id="42161",
        family=ChainFamily.EVM,
        display_name="Arbitrum",
        rpc_endpoints=[
            "https://arb1.arbitrum.io/rpc",
            "https://arb-mainnet.g.alchemy.com/v2/${ALCHEMY_KEY}",
            "https://arbitrum-one-rpc.publicnode.com",
        ],
        explorer_url="https://arbiscan.io",
        explorer_api_url="https://api.arbiscan.io/api",
        explorer_api_key_env="ARBISCAN_API_KEY",
        native_token_symbol="ETH",
        native_token_decimals=18,
        dexscreener_chain_id="arbitrum",
        api_key_env="ARBISCAN_API_KEY",
    ),
    
    "polygon": ChainConfig(
        name="polygon",
        chain_id="137",
        family=ChainFamily.EVM,
        display_name="Polygon",
        rpc_endpoints=[
            "https://polygon-mainnet.g.alchemy.com/v2/${ALCHEMY_KEY}",
            "https://polygon-rpc.com",
            "https://polygon-bor-rpc.publicnode.com",
            "https://rpc.ankr.com/polygon",
        ],
        explorer_url="https://polygonscan.com",
        explorer_api_url="https://api.polygonscan.com/api",
        explorer_api_key_env="POLYGONSCAN_API_KEY",
        native_token_symbol="MATIC",
        native_token_decimals=18,
        dexscreener_chain_id="polygon",
        api_key_env="POLYGONSCAN_API_KEY",
    ),
    
    "avalanche": ChainConfig(
        name="avalanche",
        chain_id="43114",
        family=ChainFamily.EVM,
        display_name="Avalanche",
        rpc_endpoints=[
            "https://api.avax.network/ext/bc/C/rpc",
            "https://avalanche-c-chain-rpc.publicnode.com",
            "https://rpc.ankr.com/avalanche",
        ],
        explorer_url="https://snowtrace.io",
        explorer_api_url="https://api.snowtrace.io/api",
        explorer_api_key_env="SNOWTRACE_API_KEY",
        native_token_symbol="AVAX",
        native_token_decimals=18,
        dexscreener_chain_id="avalanche",
        api_key_env="SNOWTRACE_API_KEY",
    ),
    
    "optimism": ChainConfig(
        name="optimism",
        chain_id="10",
        family=ChainFamily.EVM,
        display_name="Optimism",
        rpc_endpoints=[
            "https://mainnet.optimism.io",
            "https://opt-mainnet.g.alchemy.com/v2/${ALCHEMY_KEY}",
            "https://optimism-rpc.publicnode.com",
        ],
        explorer_url="https://optimistic.etherscan.io",
        explorer_api_url="https://api-optimistic.etherscan.io/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",  # Shares Etherscan key
        native_token_symbol="ETH",
        native_token_decimals=18,
        dexscreener_chain_id="optimism",
        api_key_env="ETHERSCAN_API_KEY",
    ),
    
    "fantom": ChainConfig(
        name="fantom",
        chain_id="250",
        family=ChainFamily.EVM,
        display_name="Fantom",
        rpc_endpoints=[
            "https://rpc.fantom.network",
            "https://fantom-rpc.publicnode.com",
            "https://rpc.ankr.com/fantom",
        ],
        explorer_url="https://ftmscan.com",
        explorer_api_url="https://api.ftmscan.com/api",
        explorer_api_key_env="FTMSCAN_API_KEY",
        native_token_symbol="FTM",
        native_token_decimals=18,
        dexscreener_chain_id="fantom",
        api_key_env="FTMSCAN_API_KEY",
    ),
    
    "linea": ChainConfig(
        name="linea",
        chain_id="59144",
        family=ChainFamily.EVM,
        display_name="Linea",
        rpc_endpoints=[
            "https://rpc.linea.build",
            "https://linea-rpc.publicnode.com",
        ],
        explorer_url="https://lineascan.build",
        explorer_api_url="https://api.lineascan.build/api",
        explorer_api_key_env="",  # LineaScan may not have public API
        native_token_symbol="ETH",
        native_token_decimals=18,
        dexscreener_chain_id="linea",
        api_key_env="",
    ),
    
    "zksync": ChainConfig(
        name="zksync",
        chain_id="324",
        family=ChainFamily.EVM,
        display_name="zkSync Era",
        rpc_endpoints=[
            "https://mainnet.era.zksync.io",
            "https://zksync-era.blockpi.network/v1/rpc/public",
        ],
        explorer_url="https://explorer.zksync.io",
        explorer_api_url="https://block-explorer-api.mainnet.zksync.io/api",
        explorer_api_key_env="",
        native_token_symbol="ETH",
        native_token_decimals=18,
        dexscreener_chain_id="zksync",
        api_key_env="",
    ),
    
    "scroll": ChainConfig(
        name="scroll",
        chain_id="534352",
        family=ChainFamily.EVM,
        display_name="Scroll",
        rpc_endpoints=[
            "https://rpc.scroll.io",
            "https://scroll-rpc.publicnode.com",
        ],
        explorer_url="https://scrollscan.com",
        explorer_api_url="https://api.scrollscan.com/api",
        explorer_api_key_env="",  # May share Etherscan key
        native_token_symbol="ETH",
        native_token_decimals=18,
        dexscreener_chain_id="scroll",
        api_key_env="ETHERSCAN_API_KEY",
    ),
    
    "mantle": ChainConfig(
        name="mantle",
        chain_id="5000",
        family=ChainFamily.EVM,
        display_name="Mantle",
        rpc_endpoints=[
            "https://rpc.mantle.xyz",
        ],
        explorer_url="https://mantlescan.xyz",
        explorer_api_url="https://api.mantlescan.xyz/api",
        explorer_api_key_env="",
        native_token_symbol="MNT",
        native_token_decimals=18,
        dexscreener_chain_id="mantle",
        api_key_env="",
    ),
}


# ─── Convenience functions ─────────────────────────────────────────

def get_chain(chain_name: str) -> Optional[ChainConfig]:
    """Get chain config by name (case-insensitive)."""
    return CHAINS.get(chain_name.lower())

def get_chain_family(chain_name: str) -> ChainFamily:
    """Determine if a chain is Solana, EVM, or other."""
    cfg = CHAINS.get(chain_name.lower())
    return cfg.family if cfg else ChainFamily.EVM

def is_solana(chain_name: str) -> bool:
    return get_chain_family(chain_name) == ChainFamily.SOLANA

def is_evm(chain_name: str) -> bool:
    return get_chain_family(chain_name) == ChainFamily.EVM

def resolve_chain_id(chain_name: str) -> str:
    """Resolve chain name to numeric or canonical ID."""
    cfg = CHAINS.get(chain_name.lower())
    return cfg.chain_id if cfg else chain_name

def list_chains() -> List[str]:
    """List all supported chain names."""
    return list(CHAINS.keys())

def get_chain_display(chain_name: str) -> str:
    """Get human-readable chain display name."""
    cfg = CHAINS.get(chain_name.lower())
    return cfg.display_name if cfg else chain_name.title()

def get_explorer_url(chain_name: str, address: str, tx: str = "") -> str:
    """Build explorer URL for an address or transaction."""
    cfg = CHAINS.get(chain_name.lower())
    if not cfg:
        return ""
    if tx:
        return f"{cfg.explorer_url}/tx/{tx}" if cfg.is_evm else f"{cfg.explorer_url}/tx/{tx}"
    if cfg.is_solana:
        return f"{cfg.explorer_url}/account/{address}"
    return f"{cfg.explorer_url}/address/{address}"

def get_rpc_urls(chain_name: str) -> List[str]:
    """Get list of RPC URLs for a chain (with env vars resolved)."""
    cfg = CHAINS.get(chain_name.lower())
    if not cfg:
        return []
    urls = []
    for url in cfg.rpc_endpoints:
        # Resolve ${VAR} references from environment
        import re
        resolved = re.sub(r'\$\{(\w+)\}', lambda m: os.getenv(m.group(1), m.group(1)), url)
        urls.append(resolved)
    return urls

def get_explorer_api_config(chain_name: str) -> Tuple[str, str]:
    """Get (api_url, api_key) for a chain's block explorer."""
    cfg = CHAINS.get(chain_name.lower())
    if not cfg:
        return ("", "")
    api_key = ""
    if cfg.api_key_env:
        api_key = os.getenv(cfg.api_key_env, "")
    return (cfg.explorer_api_url, api_key)

def get_cex_wallets(chain_name: str) -> Dict[str, List[str]]:
    """Get known CEX hot wallets for a chain."""
    cfg = CHAINS.get(chain_name.lower())
    return cfg.cex_hot_wallets if cfg else {}

def get_known_lockers(chain_name: str) -> Dict[str, str]:
    """Get known liquidity locker contracts for a chain."""
    cfg = CHAINS.get(chain_name.lower())
    return cfg.known_lockers if cfg else {}