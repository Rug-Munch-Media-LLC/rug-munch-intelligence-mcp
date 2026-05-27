"""
SENTINEL — Multi-Chain Token Security Scanner
=============================================
17 Detection Modules for comprehensive token security analysis.

Modules:
  - holder_analyzer: HHI calculation, fake diversification detection
  - bundle_detector: Enhanced bundle/sniper detection, funding chain analysis
  - exchange_funder: CEX-funded wallet detection
  - liquidity_verifier: Lock verification, fake locker detection, expiry monitoring
  - dev_reputation: Developer serial rugg detection, cross-chain portability
  - wash_trading: Circular transfer detection, cross-DEX loops
  - pumpfun_analyzer: Pump.fun bonding curve, bot detection, graduation monitoring
  - sentiment_analyzer: Sentiment scoring, bot campaign detection, pump probability
  - metadata_fingerprint: HTML structure hashing, description similarity, social overlap
  - honeypot_detector: Honeypot detection via buy/sell simulation, transfer tax analysis
  - contract_authority: Mint/freeze/update authority, proxy detection, ownership renunciation
  - mev_detector: MEV/sandwich attack detection, Jito bundle inspection, known bot tracking
  - flash_loan_detector: Flash loan attack detection, borrow-then-dump patterns
  - pump_dump_detector: Pump-and-dump lifecycle, coordinated shill, volume spike detection
  - oracle_manipulation: Oracle source/depth analysis, price manipulation vulnerability
  - governance_attack: Governance concentration, timelock/quorum risk detection
  - proxy_detector: Proxy resolution, implementation fingerprinting, upgrade risk
"""

from .holder_analyzer import HolderAnalyzer
from .bundle_detector import BundleDetector
from .exchange_funder import ExchangeFunderDetector
from .liquidity_verifier import LiquidityVerifier
from .dev_reputation import DevReputationEngine
from .wash_trading import WashTradingDetector
from .pumpfun_analyzer import PumpFunAnalyzer
from .sentiment_analyzer import SentimentAnalyzer
from .metadata_fingerprint import MetadataFingerprinter
from .honeypot_detector import HoneypotDetector, HoneypotReport
from .contract_authority import ContractAuthorityScanner, ContractAuthorityReport, run_contract_authority_scan
from .mev_detector import MEVDetector, MEVReport, SandwichAttack, MEVBotActivity
from .flash_loan_detector import FlashLoanDetector, FlashLoanReport
from .pump_dump_detector import PumpDumpDetector, PumpDumpReport
from .oracle_manipulation import OracleManipulationDetector, OracleManipulationReport
from .governance_attack import GovernanceAttackDetector, GovernanceAttackReport
from .proxy_detector import ProxyDetector, ProxyReport
from .static_analyzer import StaticAnalyzer, StaticAnalysisReport
from .decompiler_analyzer import DecompilerAnalyzer, DecompilerReport
from .address_labeler import AddressLabeler, AddressLabelReport
from .fund_flow_visualizer import FundFlowVisualizer, FundFlowReport
from .contract_diff import ContractDiffAnalyzer, ContractDiffReport
from .rag_citations import query_rag_citations, build_citation_string, query_address_rag

# Pipeline orchestrator
from .sentinel_pipeline import (
    SentinelReport,
    run_sentinel_scan,
    dataclass_to_dict,
    run_holder_analysis,
    run_bundle_detection,
    run_exchange_funding,
    run_liquidity_verification,
    run_dev_reputation,
    run_wash_trading,
    run_metadata_fingerprint,
    run_sentiment,
    run_pumpfun_analysis,
    run_honeypot_detection,
    run_contract_authority,
    run_mev_detection,
    run_flash_loan_detection,
    run_pump_dump_detection,
    run_oracle_manipulation,
    run_governance_attack,
    run_proxy_detection,
    run_static_analysis,
    run_decompiler_analysis,
    run_address_labels,
    run_fund_flow,
)

__all__ = [
    "HolderAnalyzer",
    "BundleDetector",
    "ExchangeFunderDetector",
    "LiquidityVerifier",
    "DevReputationEngine",
    "WashTradingDetector",
    "PumpFunAnalyzer",
    "SentimentAnalyzer",
    "MetadataFingerprinter",
    "HoneypotDetector",
    "HoneypotReport",
    "ContractAuthorityScanner",
    "ContractAuthorityReport",
    "run_contract_authority_scan",
    "MEVDetector",
    "MEVReport",
    "SandwichAttack",
    "MEVBotActivity",
    # Tier 2 scanners
    "FlashLoanDetector",
    "FlashLoanReport",
    "PumpDumpDetector",
    "PumpDumpReport",
    "OracleManipulationDetector",
    "OracleManipulationReport",
    "GovernanceAttackDetector",
    "GovernanceAttackReport",
    "ProxyDetector",
    "ProxyReport",
    # Tier 3 scanners
    "StaticAnalyzer",
    "StaticAnalysisReport",
    "DecompilerAnalyzer",
    "DecompilerReport",
    "AddressLabeler",
    "AddressLabelReport",
    # Tier 4 — Visualization
    "FundFlowVisualizer",
    "FundFlowReport",
    # RAG Citations
    "query_rag_citations",
    "build_citation_string",
    "query_address_rag",
    # Pipeline
    "SentinelReport",
    "run_sentinel_scan",
    "dataclass_to_dict",
    "run_holder_analysis",
    "run_bundle_detection",
    "run_exchange_funding",
    "run_liquidity_verification",
    "run_dev_reputation",
    "run_wash_trading",
    "run_metadata_fingerprint",
    "run_sentiment",
    "run_pumpfun_analysis",
    "run_flash_loan_detection",
    "run_pump_dump_detection",
    "run_oracle_manipulation",
    "run_governance_attack",
    "run_proxy_detection",
    "run_static_analysis",
    "run_decompiler_analysis",
    "run_address_labels",
    "run_fund_flow",
]