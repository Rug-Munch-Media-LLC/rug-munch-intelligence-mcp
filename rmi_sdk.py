"""
RMI Python SDK — 3-line x402 payment integration.

    from rmi import RMI
    rmi = RMI()
    result = rmi.scan("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")

Handles payment automatically via x402 protocol. No API keys needed.
Pay per use — $0.01-$0.25 per call in USDC on 13 chains.

Install: pip install rmi-mcp  (or copy this file as rmi.py)
"""

import json, os, hashlib, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from typing import Optional, Dict, Any, List

API_BASE = os.environ.get("RMI_API_BASE", "https://mcp.rugmunch.io/api/v1/x402-tools")


class RMI:
    """Rug Munch Intelligence client with automatic x402 payment handling."""

    def __init__(self, base_url: str = None):
        self.base = base_url or API_BASE
        self._fingerprint = hashlib.sha256(
            f"rmi-sdk-{os.uname().nodename}-{time.time()}".encode()
        ).hexdigest()[:32]

    def _call(self, tool: str, params: Dict = None) -> Dict:
        """Internal: call an x402 tool, handling payment flow automatically."""
        data = json.dumps(params or {}).encode()
        headers = {
            "Content-Type": "application/json",
            "x-fingerprint": self._fingerprint,
            "User-Agent": "rmi-python-sdk/1.0",
        }

        url = f"{self.base}/{tool}"
        req = Request(url, data=data, headers=headers)

        try:
            resp = urlopen(req, timeout=30)
            return json.loads(resp.read())
        except HTTPError as e:
            if e.code == 402:
                return self._handle_payment(tool, params, e)
            raise

    def _handle_payment(self, tool: str, params: Dict, error: HTTPError) -> Dict:
        """Handle 402 Payment Required — guide user to pay."""
        body = json.loads(error.read())
        resource = body.get("resource", {})
        accepts = body.get("accepts", [])

        # Find cheapest payment option
        cheapest = min(accepts, key=lambda a: int(a.get("amount", "0")))
        network = cheapest.get("network", "unknown")
        pay_to = cheapest.get("payTo", "")
        amount = int(cheapest.get("amount", 0))
        asset_info = cheapest.get("extra", {})

        price_usd = amount / 1_000_000 if "USDC" in str(asset_info.get("name", "")) else amount / 1e9

        return {
            "error": "payment_required",
            "tool": tool,
            "price_usd": round(price_usd, 5),
            "amount_atoms": str(amount),
            "pay_to": pay_to,
            "network": network,
            "message": f"Send {price_usd} USDC to {pay_to} on {network}. Then retry with tx_hash.",
            "retry_with": {"tx_hash": "0x..."},
            "_raw_402": body,
        }

    def pay_and_call(self, tool: str, params: Dict, tx_hash: str) -> Dict:
        """Call a tool with a payment transaction hash."""
        params = dict(params or {})
        params["tx_hash"] = tx_hash
        headers = {
            "Content-Type": "application/json",
            "x-fingerprint": self._fingerprint,
            "x-pay": tx_hash,
            "User-Agent": "rmi-python-sdk/1.0",
        }
        req = Request(f"{self.base}/{tool}", data=json.dumps(params).encode(), headers=headers)
        try:
            resp = urlopen(req, timeout=30)
            return json.loads(resp.read())
        except HTTPError as e:
            return json.loads(e.read()) if e.fp else {"error": str(e.code)}

    # ── Convenience Methods ──────────────────────────────

    def scan(self, address: str, chain: str = "base") -> Dict:
        """Quick security scan — returns risk score, labels, and flags."""
        return self._call("reputation_score", {"address": address, "chain": chain})

    def audit(self, address: str, chain: str = "base") -> Dict:
        """Deep contract audit — liquidity, holders, risk analysis."""
        return self._call("audit", {"address": address, "chain": chain})

    def report(self, address: str, chain: str = "base", depth: str = "standard") -> Dict:
        """Full investigation report — reputation, forensics, recommendation."""
        return self._call("investigation_report", {"address": address, "chain": chain, "depth": depth})

    def watch(self, webhook_url: str, events: List[str] = None, address: str = None, chain: str = "all") -> Dict:
        """Register a webhook for real-time alerts."""
        return self._call("webhook_register", {
            "url": webhook_url,
            "events": events or ["rug_pull", "whale_move", "price_crash"],
            "address": address,
            "chain": chain,
        })

    def reputation(self, address: str, chain: str = "base") -> Dict:
        """Get trust score 0-100 for any address."""
        return self._call("reputation_score", {"address": address, "chain": chain})

    def wallet(self, address: str, chain: str = "base") -> Dict:
        """Wallet profiling — balance, transactions, persona."""
        return self._call("wallet", {"address": address, "chain": chain})

    def honeypot(self, address: str, chain: str = "base") -> Dict:
        """Check if a token is a honeypot scam."""
        return self._call("honeypot_check", {"address": address, "chain": chain})


# ── Quick one-shot functions ──────────────────────────────

_default = None

def _get_default():
    global _default
    if _default is None:
        _default = RMI()
    return _default

def scan(address: str, chain: str = "base") -> Dict:
    return _get_default().scan(address, chain)

def audit(address: str, chain: str = "base") -> Dict:
    return _get_default().audit(address, chain)

def reputation(address: str, chain: str = "base") -> Dict:
    return _get_default().reputation(address, chain)

def report(address: str, chain: str = "base") -> Dict:
    return _get_default().report(address, chain)


if __name__ == "__main__":
    # Quick test
    rmi = RMI()
    print("RMI SDK v1.0 — Ready")
    print(f"Endpoint: {rmi.base}")
    print(f"Try: rmi.scan('0x...') or scan('0x...')")
