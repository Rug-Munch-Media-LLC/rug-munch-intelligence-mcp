"""
X402 Tool Data Provider — Cached, rate-limited data access for all x402 tools.

Replace raw aiohttp/httpx calls with this provider. One import, everything cached.

Usage in x402 routers:
    from app.caching_shield.tool_data import td
    
    # Instead of: async with aiohttp.ClientSession() as s: r = await s.get(url)
    # Use: result = await td.token_price(mint="So111...")
    # Returns: {"price_usd": 79.5, "source": "jupiter", "cached": False}
"""

from app.caching_shield.unified_layer import get_data_layer, ToolResult

class ToolData:
    """Cached, rate-limited data provider for x402 tool routers."""

    def __init__(self):
        self._layer = get_data_layer()

    async def token_price(self, mint: str) -> dict:
        r = await self._layer.fetch("token_price", mint=mint)
        return r.to_dict() if r else {"error": "no data"}

    async def token_meta(self, mint: str) -> dict:
        r = await self._layer.fetch("token_meta", mint=mint)
        return r.to_dict() if r else {"error": "no data"}

    async def wallet_balance(self, address: str) -> dict:
        r = await self._layer.fetch("wallet_balance", address=address)
        return r.to_dict() if r else {"error": "no data"}

    async def risk_scan(self, address: str, chain: str = "solana") -> dict:
        r = await self._layer.fetch("risk_scan", address=address, chain=chain)
        return r.to_dict() if r else {"error": "no data"}

    async def tx_history(self, address: str) -> dict:
        r = await self._layer.fetch("tx_history", address=address)
        return r.to_dict() if r else {"error": "no data"}

    async def funding_source(self, address: str, chain_id: int = 1) -> dict:
        r = await self._layer.fetch("funding_source", address=address, chain_id=chain_id)
        return r.to_dict() if r else {"error": "no data"}

    def stats(self) -> dict:
        return self._layer.stats()


# Singleton
td = ToolData()
