"""
x402 Multi-Facilitator Registry
================================
Pluggable facilitator modules for payment verification and settlement.
Each facilitator implements the base.Facilitator interface.

Architecture:
    Payment Request → Smart Router → Best Facilitator → Verify/Settle
                                                   ↓ (fallback)
                                              Next Facilitator

Supported Facilitators:
    Hosted:
        - Coinbase CDP (Base, instant settlement)
        - PayAI (Base, Solana, deferred)
        - Cloudflare x402 (Base, Ethereum)
        - BNB Pieverse (BNB Chain)
        - AsterPay (EUR/SEPA, European)
        - MERX x402 (TRON: USDT/USDC/USDD)
        - Primev FastRPC (Ethereum, fee-free, mev-commit)
        - Satoshi (Bitcoin → Base/Solana)
    Self-Hosted:
        - x402-rs (multi-chain Rust facilitator)
    Universal:
        - EIP-7702 (all EVM chains, all tokens, all native coins)
"""
from app.facilitators.base import Facilitator, FacilitatorRegistry, VerificationResult, SettlementResult
from app.facilitators.router import FacilitatorRouter, get_facilitator_router

__all__ = [
    "Facilitator",
    "FacilitatorRegistry",
    "FacilitatorRouter",
    "get_facilitator_router",
    "VerificationResult",
    "SettlementResult",
]
