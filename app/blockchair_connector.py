"""
Blockchair API Integration - Bitcoin/Litecoin/Ethereum/Solana Blockchain API
============================================================================

Access blockchain data for:
- Transaction lookups
- Address balance checks
- Block information
- Transaction status
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


# ─── BLOCKCHAIR API ENDPOINTS ─────────────────────────────────────

BLOCKCHAIR_API = "https://api.blockchair.com"

ENDPOINTS = {
    "bitcoin": "/bitcoin",
    "ethereum": "/ethereum",
    "solana": "/solana",
    "litecoin": "/litecoin",
    "bitcoin_cash": "/bitcoin-cash",
    "bitcoin_sv": "/bitcoin-sv",
    "search": "/v2/search",
    "stats": "/v2/stats",
    "block": "/v2/block/{chain}/{id}",
    "address": "/v2/address/{chain}/{address}",
    "transaction": "/v2/transaction/{chain}/{hash}",
    "mempool": "/v2/mempool/{chain}",
}


# ─── BLOCKCHAIR CLIENT ────────────────────────────────────────────

class BlockchairClient:
    """Client for Blockchair API."""
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self.api_key = api_key or ""
        self.timeout = timeout
        self._available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if Blockchair API is accessible."""
        try:
            # Public API - no key required for basic access
            response = requests.get(f"{BLOCKCHAIR_API}/bitcoin/stats", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_chain_stats(self, chain: str = "bitcoin") -> Dict[str, Any]:
        """
        Get blockchain statistics.
        
        Args:
            chain: Chain name (bitcoin, ethereum, solana, etc.)
            
        Returns:
            Chain statistics
        """
        endpoint = ENDPOINTS.get(chain, "/bitcoin")
        try:
            response = requests.get(
                f"{BLOCKCHAIR_API}{endpoint}/stats",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()["data"]["stats"]
        except Exception as e:
            logger.error(f"Error fetching stats for {chain}: {e}")
            return {}
    
    def get_address_info(self, address: str, chain: str = "bitcoin") -> Optional[Dict[str, Any]]:
        """
        Get address information.
        
        Args:
            address: Blockchain address
            chain: Chain name
            
        Returns:
            Address data or None
        """
        try:
            response = requests.get(
                f"{BLOCKCHAIR_API}{ENDPOINTS['address'].format(chain=chain, address=address)}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()["data"][address]
        except Exception as e:
            logger.error(f"Error fetching address {address} info: {e}")
            return None
    
    def get_transaction(self, tx_hash: str, chain: str = "bitcoin") -> Optional[Dict[str, Any]]:
        """
        Get transaction details.
        
        Args:
            tx_hash: Transaction hash
            chain: Chain name
            
        Returns:
            Transaction data or None
        """
        try:
            response = requests.get(
                f"{BLOCKCHAIR_API}{ENDPOINTS['transaction'].format(chain=chain, hash=tx_hash)}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()["data"][tx_hash]
        except Exception as e:
            logger.error(f"Error fetching transaction {tx_hash}: {e}")
            return None
    
    def search(self, query: str) -> Dict[str, Any]:
        """
        Search for addresses, transactions, blocks.
        
        Args:
            query: Search query
            
        Returns:
            Search results
        """
        try:
            response = requests.get(
                f"{BLOCKCHAIR_API}{ENDPOINTS['search']}",
                params={"query": query},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return {}
    
    def get_blocks(self, chain: str = "bitcoin", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent blocks.
        
        Args:
            chain: Chain name
            limit: Number of blocks
            
        Returns:
            List of block data
        """
        try:
            response = requests.get(
                f"{BLOCKCHAIR_API}{ENDPOINTS.get(chain, '/bitcoin')}/blocks",
                params={"limit": limit},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            logger.error(f"Error fetching blocks for {chain}: {e}")
            return []
    
    def get_mempool(self, chain: str) -> Dict[str, Any]:
        """
        Get mempool status.
        
        Args:
            chain: Chain name
            
        Returns:
            Mempool data
        """
        try:
            response = requests.get(
                f"{BLOCKCHAIR_API}{ENDPOINTS['mempool'].format(chain=chain)}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            logger.error(f"Error fetching mempool for {chain}: {e}")
            return {}
    
    def get_block(self, chain: str, block_id: int) -> Optional[Dict[str, Any]]:
        """
        Get specific block data.
        
        Args:
            chain: Chain name
            block_id: Block number or hash
            
        Returns:
            Block data or None
        """
        try:
            response = requests.get(
                f"{BLOCKCHAIR_API}{ENDPOINTS['block'].format(chain=chain, id=block_id)}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            logger.error(f"Error fetching block {block_id} for {chain}: {e}")
            return None


# ─── GLOBAL SINGLETON ─────────────────────────────────────────────

_client: Optional[BlockchairClient] = None


def get_blockchair_client(chain: str = "bitcoin") -> BlockchairClient:
    """Get or create Blockchair client instance."""
    global _client
    if _client is None:
        _client = BlockchairClient()
    return _client


def get_address_balance(address: str, chain: str = "bitcoin") -> Optional[Dict[str, Any]]:
    """Get address balance from Blockchair."""
    client = get_blockchair_client(chain)
    return client.get_address_info(address)


def search_blockchain(query: str) -> Dict[str, Any]:
    """Search Blockchair for blockchain data."""
    client = get_blockchair_client()
    return client.search(query)
