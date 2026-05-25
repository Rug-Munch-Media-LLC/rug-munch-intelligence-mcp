"""
Expanded tool aliases — maps 44 new specialized tools + 80 per-chain variants
to their closest real handler endpoint.

Per-chain variants (e.g., wallet_solana) are handled by the dispatcher
automatically via the base_tool field in TOOL_PRICES.
This file only maps the 44 brand-new tool names.
"""

EXPANDED_ALIASES = {
    # Security → audit (deep contract analysis) or other specific handlers
    "flash_loan_detect": "audit",
    "governance_attack": "audit",
    "contract_upgrade_monitor": "audit",
    "reentrancy_scanner": "audit",
    "wallet_drain_scanner": "audit",
    "dust_attack_detect": "urlcheck",
    "oracle_manipulation": "audit",
    "privilege_escalation": "audit",
    "phantom_mint_detect": " honeypot_check",

    # Intelligence
    "cross_chain_whale": "whale",
    "degen_score": "smart_money_alpha",
    "wallet_cluster_score": "cluster",
    "dormant_whale_alert": "whale",
    "smart_contract_interactions": "wallet",
    "token_distribution_health": "wallet",
    "token_velocity": "pulse",
    "wallet_label_registry": "wallet",

    # Market
    "funding_rate": "market_overview",
    "options_flow": "market_overview",
    "dex_volume_rank": "market_overview",
    "liquidation_heatmap": "market_overview",
    "volatility_surface": "market_overview",
    "stablecoin_flow": "market_overview",

    # Social
    "reddit_sentiment": "sentiment",
    "discord_alpha": "social_signal",
    "telegram_pump_detect": "sentiment",
    "influencer_impact_score": "social_signal",
    "github_developer_activity": "social_signal",

    # Analysis
    "correlation_matrix": "portfolio_tracker",
    "volume_profile": "pulse",
    "orderbook_imbalance": "market_overview",
    "drawdown_analyzer": "portfolio_tracker",
    "sharpe_ratio_calc": "portfolio_tracker",
    "sector_rotation": "market_overview",
    "nft_floor_analytics": "market_overview",
    "tax_lot_optimizer": "portfolio_tracker",

    # Launchpad
    "presale_scanner": "launch",
    "ido_tracker": "launch_intel",
    "fair_launch_detect": "launch",
    "vesting_schedule_analyzer": "market_overview",

    # Premium
    "deep_forensics": "forensics",
    "whale_network_map": "cluster",
    "cross_chain_trace": "insider",
    "full_wallet_dossier": "comprehensive_audit",

    # DeFi
    "yield_aggregator": "defi_yield_scanner",
    "impermanent_loss": "defi_yield_scanner",
}