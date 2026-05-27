"""
Wallet Memory Bank — Persistent wallet intelligence across chains.
===============================================================
Consolidates wallet clustering, labeling, entity resolution, and risk scoring
into a single coherent system that feeds SENTINEL token scans and powers
standalone wallet exploration.

Two products, one backbone:
  - SENTINEL (token scanner) consumes deployer intelligence from here
  - WalletSafe (wallet explorer) surfaces entity graphs and risk profiles
"""

from .engine import WalletMemoryEngine, get_wallet_engine

__all__ = ["WalletMemoryEngine", "get_wallet_engine"]