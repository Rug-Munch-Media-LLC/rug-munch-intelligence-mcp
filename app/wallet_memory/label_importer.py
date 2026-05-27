"""
Static Label Importer — Async boot-time loader for 105K+ wallet labels.
========================================================================
Replaces the sync Redis-only wallet_label_loader.py with an async module that:

1. Downloads/locates crypto-wallet-address-labels datasets (Solana CEX, DApp, DeFi)
2. Loads etherscan CSVs from /root/backend/data/
3. Fetches OFAC crypto-sanctions-list
4. Stores everything through WalletStorage (Redis cache + ClickHouse)

Sources:
  - crypto-wallet-address-labels GitHub (105K+ Solana)
  - etherscan_combined_labels.csv (50K rows)
  - etherscan_phish_hack.csv (111 rows)
  - OFAC crypto-sanctions-list
"""

import asyncio
import csv
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("wallet_memory.label_importer")

# ── Paths ──────────────────────────────────────────────────────────────

DATA_DIR = os.getenv("RMI_DATA_DIR", "/app/data")
LABELS_DIR = os.path.join(DATA_DIR, "wallet-labels")
ETHERSCAN_COMBINED = os.path.join(DATA_DIR, "etherscan_combined_labels.csv")
ETHERSCAN_PHISH_HACK = os.path.join(DATA_DIR, "etherscan_phish_hack.csv")

# GitHub base for Solana label CSVs
SOLANA_LABELS_REPO = (
    "https://raw.githubusercontent.com/ImMike/"
    "crypto-wallet-address-labels/main/datasets/solana-wallet-and-program-labels"
)

# OFAC sanctions URL
OFAC_URL = (
    "https://raw.githubusercontent.com/OFAC/"
    "crypto-sanctions-list/main/crypto-sanctions-list.json"
)

# Solana label file specs: (filename, chain, address_col, label_col_map)
SOLANA_CSV_SPECS = [
    ("solana_cex_labels.csv", "solana", "address", {
        "label_type": "label_type", "label_subtype": "label_subtype",
        "name": "address_name", "project": "project_name",
    }),
    ("solana_dapp_labels.csv", "solana", "address", {
        "name": "dapp_name",
    }),
    ("solana_defi_labels.csv", "solana", "address", {
        "name": "protocol_name",
    }),
]

# Additional Ethereum phishing/scam CSV specs from the same repo
ETH_CSV_SPECS = [
    ("phishing_scams.csv", "ethereum", "address", {
        "name": "etherscan_tag", "label_type": "etherscan_labels",
    }),
    ("etherscan_malicious_labels.csv", "ethereum", "banned_address", {
        "name": "wallet_tag", "label_type": "data_source",
    }),
    ("malicious_smart_contracts.csv", "ethereum", "contract_address", {
        "name": "contract_tag", "label_type": "source",
    }),
]

# ClickHouse DDL for wallet_labels table (added to schema on first run)
WALLET_LABELS_DDL = """
CREATE TABLE IF NOT EXISTS wallet_labels (
    address         String,
    chain_id        LowCardinality(String),
    label_name      String DEFAULT '',
    label_category  LowCardinality(String) DEFAULT '',
    label_subtype   String DEFAULT '',
    source          LowCardinality(String) DEFAULT '',
    is_sanctioned   UInt8 DEFAULT 0,
    loaded_at       DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(loaded_at)
ORDER BY (address, chain_id, source);
"""

# ── Download helpers ────────────────────────────────────────────────────

_http_client: Optional[httpx.AsyncClient] = None


async def _get_http() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=30.0, follow_redirects=True,
            headers={"User-Agent": "RMI-LabelImporter/1.0"},
        )
    return _http_client


async def _download_file(url: str, dest: str) -> bool:
    """Download a URL to dest path. Returns True on success."""
    try:
        client = await _get_http()
        resp = await client.get(url)
        if resp.status_code != 200:
            logger.warning(f"Download failed {url}: HTTP {resp.status_code}")
            return False
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(resp.content)
        logger.info(f"Downloaded {url} -> {dest} ({len(resp.content)} bytes)")
        return True
    except Exception as e:
        logger.warning(f"Download error {url}: {e}")
        return False


async def _download_json(url: str) -> Optional[Any]:
    """Download and parse JSON from URL. Returns None on failure."""
    try:
        client = await _get_http()
        resp = await client.get(url)
        if resp.status_code != 200:
            logger.warning(f"JSON download failed {url}: HTTP {resp.status_code}")
            return None
        return resp.json()
    except Exception as e:
        logger.warning(f"JSON download error {url}: {e}")
        return None


# ── Solana labels ──────────────────────────────────────────────────────

async def _ensure_solana_labels() -> Dict[str, int]:
    """Download Solana label CSVs if not present. Returns {filename: size}."""
    os.makedirs(LABELS_DIR, exist_ok=True)
    results = {}
    for filename, _, _, _ in SOLANA_CSV_SPECS:
        dest = os.path.join(LABELS_DIR, filename)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            size = os.path.getsize(dest)
            logger.info(f"Solana labels already present: {filename} ({size} bytes)")
            results[filename] = size
        else:
            url = f"{SOLANA_LABELS_REPO}/{filename}"
            ok = await _download_file(url, dest)
            results[filename] = os.path.getsize(dest) if ok else 0
            if not ok:
                logger.warning(f"Failed to download {filename} — skipping")
    return results


# ── OFAC sanctions ─────────────────────────────────────────────────────

async def _load_ofac_sanctions(storage) -> int:
    """
    Load OFAC crypto-sanctions-list into storage.
    Tries local file first, then downloads from GitHub.
    """
    # Try local cached copy first
    local_ofac = os.path.join(LABELS_DIR, "ofac_sanctions.json")
    sanctions = None

    if os.path.exists(local_ofac) and os.path.getsize(local_ofac) > 0:
        try:
            with open(local_ofac, encoding="utf-8") as f:
                sanctions = json.load(f)
            logger.info(f"Loaded OFAC from local cache ({len(sanctions)} entries)")
        except Exception as e:
            logger.warning(f"Local OFAC file corrupt: {e}")
            sanctions = None

    if sanctions is None:
        sanctions = await _download_json(OFAC_URL)
        if sanctions is None:
            logger.warning("OFAC sanctions download failed — trying fallback")
            # Fallback: try alternate URL formats
            alt_urls = [
                "https://raw.githubusercontent.com/OFAC/crypto-sanctions-list/master/crypto-sanctions-list.json",
                "https://raw.githubusercontent.com/OFAC/crypto-sanctions-list/main/crypto_sanctions_list.json",
            ]
            for alt in alt_urls:
                sanctions = await _download_json(alt)
                if sanctions is not None:
                    break

    if sanctions is None:
        logger.error("OFAC sanctions unavailable from all sources")
        return 0

    # Save local cache for next boot
    try:
        os.makedirs(LABELS_DIR, exist_ok=True)
        with open(local_ofac, "w", encoding="utf-8") as f:
            json.dump(sanctions, f)
    except Exception:
        pass

    # Store in Redis and ClickHouse
    count = 0
    ch_rows = []
    for entry in sanctions:
        addr = ""
        if isinstance(entry, dict):
            addr = entry.get("address", entry.get("Address", ""))
        if not addr or len(str(addr).strip()) < 10:
            continue

        addr_lower = str(addr).strip().lower()
        entry_json = json.dumps(entry)

        # Redis: rmi:label:ofac:{address}
        await storage.redis_set(f"rmi:label:ofac:{addr_lower}", entry_json)
        await storage.redis_sadd("rmi:labels:ofac", addr_lower)

        # ClickHouse row
        name = ""
        if isinstance(entry, dict):
            name = entry.get("name", entry.get("Name", entry.get("entity", "")))
        ch_rows.append((
            addr_lower, "", str(name) if name else "OFAC Sanctioned",
            "sanctioned", "", "ofac", 1,
            datetime.now(timezone.utc),
        ))
        count += 1

    # Batch insert to ClickHouse
    if ch_rows and storage._ch:
        try:
            storage._ch.execute(
                """INSERT INTO wallet_labels
                (address, chain_id, label_name, label_category, label_subtype,
                 source, is_sanctioned, loaded_at) VALUES""",
                ch_rows,
            )
        except Exception as e:
            logger.warning(f"ClickHouse OFAC batch insert failed: {e}")

    await storage.redis_set("rmi:labels:ofac:count", str(count))
    logger.info(f"Loaded {count} OFAC sanctions")
    return count


# ── CSV loading ─────────────────────────────────────────────────────────

async def _load_csv_labels(
    storage,
    path: str,
    chain: str,
    addr_col: str,
    label_cols: Dict[str, str],
    source_name: str = "",
) -> int:
    """
    Load a CSV of labeled addresses into Redis + ClickHouse via WalletStorage.
    Returns count of addresses loaded.
    """
    if not os.path.exists(path):
        logger.warning(f"CSV not found: {path}")
        return 0

    src = source_name or os.path.basename(path)
    count = 0
    ch_rows = []
    redis_pipe_ops = []  # Collect for batch Redis ops

    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # Normalize headers to lowercase for case-insensitive matching
            if reader.fieldnames:
                reader.fieldnames = [h.lower().strip() for h in reader.fieldnames]
            for row in reader:
                addr = row.get(addr_col, "").strip().lower()
                if not addr or len(addr) < 10:
                    continue

                # Build label data dict
                label = {"chain": chain, "address": addr, "source": src}
                for key, col in label_cols.items():
                    val = row.get(col, "").strip()
                    if val:
                        label[key] = val

                # Also pick up any extra columns we recognise
                for extra in ("name", "label", "label_type", "label_subtype"):
                    if extra not in label:
                        val = row.get(extra, "").strip()
                        if val:
                            label[extra] = val

                label_json = json.dumps(label)

                # Redis: rmi:label:{chain}:{address} (matching wallet_label_loader format)
                redis_key = f"rmi:label:{chain}:{addr}"
                redis_pipe_ops.append((redis_key, label_json, addr))

                # ClickHouse row
                name = label.get("address_name", label.get("dapp_name",
                       label.get("protocol_name", label.get("name", ""))))
                category = label.get("label_type", label.get("label", ""))
                subtype = label.get("label_subtype", "")
                ch_rows.append((
                    addr, chain,
                    str(name) if name else "",
                    str(category) if category else "",
                    str(subtype) if subtype else "",
                    src, 0,
                    datetime.now(timezone.utc),
                ))

                count += 1

                # Flush in batches of 5000
                if count % 5000 == 0:
                    await _flush_batch(storage, redis_pipe_ops, ch_rows, chain)
                    redis_pipe_ops = []
                    ch_rows = []

    except Exception as e:
        logger.warning(f"Failed to load CSV {path}: {e}")

    # Flush remaining
    if redis_pipe_ops or ch_rows:
        await _flush_batch(storage, redis_pipe_ops, ch_rows, chain)

    logger.info(f"Loaded {count} labels from {src} (chain={chain})")
    return count


async def _flush_batch(
    storage,
    redis_ops: List[Tuple[str, str, str]],
    ch_rows: List[tuple],
    chain: str,
):
    """Flush a batch of Redis writes and ClickHouse inserts."""
    # Batch Redis writes
    if storage._redis and redis_ops:
        try:
            async with storage._redis.pipeline() as pipe:
                for redis_key, label_json, addr in redis_ops:
                    pipe.set(redis_key, label_json)
                    pipe.sadd(f"rmi:labels:{chain}", addr)
                await pipe.execute()
        except Exception as e:
            # Fallback: individual writes
            logger.debug(f"Redis pipeline failed, falling back: {e}")
            for redis_key, label_json, addr in redis_ops:
                await storage.redis_set(redis_key, label_json)
                await storage.redis_sadd(f"rmi:labels:{chain}", addr)

    # Batch ClickHouse insert
    if ch_rows and storage._ch:
        try:
            storage._ch.execute(
                """INSERT INTO wallet_labels
                (address, chain_id, label_name, label_category, label_subtype,
                 source, is_sanctioned, loaded_at) VALUES""",
                ch_rows,
            )
        except Exception as e:
            logger.warning(f"ClickHouse batch insert failed: {e}")


# ── Etherscan combined labels ──────────────────────────────────────────

async def _load_etherscan_combined(storage) -> int:
    """
    Load etherscan_combined_labels.csv.
    Columns: address, name, label, chain, source
    """
    if not os.path.exists(ETHERSCAN_COMBINED):
        logger.warning(f"Etherscan combined labels not found: {ETHERSCAN_COMBINED}")
        return 0

    count = 0
    ch_rows = []
    redis_ops = []

    try:
        with open(ETHERSCAN_COMBINED, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                addr = row.get("address", "").strip().lower()
                if not addr or len(addr) < 10:
                    continue

                chain_raw = row.get("chain", "ethereum").strip().lower()
                # Normalize chain names
                chain = _normalize_chain(chain_raw)

                name = row.get("name", "").strip()
                label = row.get("label", "").strip()
                source = row.get("source", "etherscan").strip()

                label_data = {
                    "chain": chain,
                    "address": addr,
                    "address_name": name,
                    "label_type": label,
                    "source": f"etherscan_combined",
                }
                label_json = json.dumps(label_data)

                redis_key = f"rmi:label:{chain}:{addr}"
                redis_ops.append((redis_key, label_json, addr))

                ch_rows.append((
                    addr, chain, name, label, "", "etherscan_combined",
                    0, datetime.now(timezone.utc),
                ))

                count += 1

                if count % 5000 == 0:
                    await _flush_batch(storage, redis_ops, ch_rows, chain)
                    redis_ops = []
                    ch_rows = []

    except Exception as e:
        logger.warning(f"Failed to load etherscan combined: {e}")

    if redis_ops or ch_rows:
        await _flush_batch(storage, redis_ops, ch_rows, "ethereum")

    logger.info(f"Loaded {count} etherscan combined labels")
    return count


# ── Etherscan phishing/hack labels ─────────────────────────────────────

async def _load_etherscan_phish_hack(storage) -> int:
    """
    Load etherscan_phish_hack.csv.
    Columns: address, name_tag, label_type, chain, balance, txn_count, source
    """
    if not os.path.exists(ETHERSCAN_PHISH_HACK):
        logger.warning(f"Etherscan phish/hack not found: {ETHERSCAN_PHISH_HACK}")
        return 0

    count = 0
    ch_rows = []
    redis_ops = []

    try:
        with open(ETHERSCAN_PHISH_HACK, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                addr = row.get("address", "").strip().lower()
                if not addr or len(addr) < 10:
                    continue

                chain_raw = row.get("chain", "ethereum").strip().lower()
                chain = _normalize_chain(chain_raw)

                name_tag = row.get("name_tag", "").strip()
                label_type = row.get("label_type", "").strip()
                balance = row.get("balance", "").strip()
                txn_count = row.get("txn_count", "").strip()

                label_data = {
                    "chain": chain,
                    "address": addr,
                    "address_name": name_tag,
                    "label_type": label_type,
                    "source": "etherscan_phish_hack",
                }
                if balance:
                    label_data["balance"] = balance
                if txn_count:
                    label_data["txn_count"] = txn_count

                label_json = json.dumps(label_data)
                redis_key = f"rmi:label:{chain}:{addr}"
                redis_ops.append((redis_key, label_json, addr))

                # These are phishing/hack labels — also store in scam_addresses
                is_scam = 1 if label_type.lower() in ("scam", "phishing", "hack") else 0

                ch_rows.append((
                    addr, chain, name_tag, label_type, "", "etherscan_phish_hack",
                    is_scam, datetime.now(timezone.utc),
                ))

                # Also add to the scam_addresses ClickHouse table
                if is_scam and storage._ch:
                    try:
                        storage._ch.execute(
                            """INSERT INTO scam_addresses
                            (address, chain_id, source, threat_type, confidence,
                             first_seen_at, evidence) VALUES""",
                            [(addr, chain, "etherscan_phish_hack", label_type,
                              0.95, datetime.now(timezone.utc),
                              json.dumps({"name_tag": name_tag, "balance": balance}))],
                        )
                    except Exception:
                        pass

                count += 1

    except Exception as e:
        logger.warning(f"Failed to load etherscan phish/hack: {e}")

    if redis_ops or ch_rows:
        await _flush_batch(storage, redis_ops, ch_rows, "ethereum")

    logger.info(f"Loaded {count} etherscan phish/hack labels")
    return count


# ── Chain normalization ─────────────────────────────────────────────────

_CHAIN_ALIASES = {
    "eth": "ethereum",
    "eth_mainnet": "ethereum",
    "bsc": "bsc",
    "bnb": "bsc",
    "bnb_chain": "bsc",
    "polygon": "polygon",
    "matic": "polygon",
    "arbitrum": "arbitrum",
    "arb": "arbitrum",
    "optimism": "optimism",
    "op": "optimism",
    "avalanche": "avalanche",
    "avax": "avalanche",
    "fantom": "fantom",
    "ftm": "fantom",
    "base": "base",
    "sol": "solana",
    "solana": "solana",
}


def _normalize_chain(chain: str) -> str:
    """Normalize chain name to canonical form."""
    return _CHAIN_ALIASES.get(chain.lower().strip(), chain.lower().strip()) or "ethereum"


# ── ClickHouse schema ───────────────────────────────────────────────────

async def _ensure_wallet_labels_table(storage):
    """Create the wallet_labels table in ClickHouse if it doesn't exist."""
    if not storage._ch:
        return
    try:
        storage._ch.execute(
            "CREATE DATABASE IF NOT EXISTS wallet_memory"
        )
        storage._ch.execute(WALLET_LABELS_DDL)
        logger.info("wallet_labels table ensured in ClickHouse")
    except Exception as e:
        logger.warning(f"Failed to create wallet_labels table: {e}")


# ── Main entry point ────────────────────────────────────────────────────

_loading = False
_last_load_counts: Dict[str, int] = {}


async def load_all_static_labels() -> Dict[str, int]:
    """
    Load all static wallet label datasets on boot.

    Sources:
      1. Solana CEX labels (crypto-wallet-address-labels GitHub)
      2. Solana DApp labels
      3. Solana DeFi labels
      4. Etherscan combined labels (50K rows)
      5. Etherscan phishing/hack labels (111 rows)
      6. OFAC crypto sanctions

    Returns counts per source.
    """
    global _loading, _last_load_counts

    if _loading:
        logger.info("Label import already in progress — skipping")
        return _last_load_counts

    _loading = True
    start = time.time()
    counts: Dict[str, int] = {}

    try:
        from .storage import get_storage
        storage = get_storage()

        # Ensure connections
        await storage._ensure_connections()
        logger.info(
            f"Storage connections: redis={'ok' if storage._redis else 'no'}, "
            f"clickhouse={'ok' if storage._ch else 'no'}"
        )

        # Ensure ClickHouse table exists
        await _ensure_wallet_labels_table(storage)

        # 1. Download Solana label CSVs if needed
        await _ensure_solana_labels()

        # 2. Load Solana CSVs
        for filename, chain, addr_col, label_cols in SOLANA_CSV_SPECS:
            path = os.path.join(LABELS_DIR, filename)
            key = filename.replace(".csv", "").replace("_labels", "")
            if os.path.exists(path):
                c = await _load_csv_labels(storage, path, chain, addr_col,
                                           label_cols, source_name=key)
                counts[key] = c
            else:
                counts[key] = 0
                logger.warning(f"Solana labels missing: {filename}")

        # 2b. Load additional ETH phishing/scam CSVs from wallet-labels dir
        for filename, chain, addr_col, label_cols in ETH_CSV_SPECS:
            path = os.path.join(LABELS_DIR, filename)
            key = filename.replace(".csv", "").replace("_labels", "")
            if os.path.exists(path):
                c = await _load_csv_labels(storage, path, chain, addr_col,
                                           label_cols, source_name=key)
                counts[key] = c
            else:
                counts[key] = 0

        # 3. Load Etherscan combined labels
        counts["etherscan_combined"] = await _load_etherscan_combined(storage)

        # 4. Load Etherscan phishing/hack labels
        counts["etherscan_phish_hack"] = await _load_etherscan_phish_hack(storage)

        # 5. Load OFAC sanctions
        counts["ofac"] = await _load_ofac_sanctions(storage)

        # Store aggregate counts in Redis
        total = sum(counts.values())
        counts["total"] = total
        await storage.redis_set("rmi:labels:counts", json.dumps(counts))

        elapsed = time.time() - start
        logger.info(
            f"Static label import complete: {total} labels in {elapsed:.1f}s — {counts}"
        )

    except Exception as e:
        logger.error(f"Static label import failed: {e}", exc_info=True)
        counts["error"] = str(e)
    finally:
        _loading = False

    _last_load_counts = counts
    return counts


def get_last_load_counts() -> Dict[str, int]:
    """Return counts from the most recent label import."""
    return _last_load_counts


def is_loading() -> bool:
    """Check if a label import is currently in progress."""
    return _loading