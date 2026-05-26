#!/usr/bin/env python3
"""Refresh TTL on existing RAG keys to match new persistence policy."""
import subprocess, sys

def redis_cli(*args):
    result = subprocess.run(
        ["docker", "exec", "rmi-redis", "redis-cli", "-a", REDIS_PASS, *args],
        capture_output=True, text=True
    )
    return result.stdout.strip()

# Get Redis password from container env
env_out = subprocess.run(
    ["docker", "exec", "rmi-backend", "env"],
    capture_output=True, text=True
).stdout
REDIS_PASS = ""
for line in env_out.splitlines():
    if line.startswith("REDIS_PASSWORD="):
        REDIS_PASS = line.split("=", 1)[1]
        break

if not REDIS_PASS:
    print("ERROR: Could not find REDIS_PASSWORD")
    sys.exit(1)

# TTL policy: 0 = persist (no expiry), N = seconds
TTL_POLICY = {
    "scam_patterns": 0,       # permanent
    "contract_audits": 0,     # permanent
    "transaction_patterns": 0, # permanent
    "forensic_reports": 0,    # permanent
    "known_scams": 0,         # permanent (was 365d)
    "wallet_profiles": 86400 * 365,  # 1 year
    "market_intel": 86400 * 365,     # 1 year
    "token_analysis": 86400 * 90,    # 90 days
    "news_articles": 86400 * 30,     # 30 days
    "general": 86400 * 30,           # 30 days
}

total = 0
persisted = 0
refreshed = 0

for collection, desired_ttl in TTL_POLICY.items():
    # Scan all keys in this collection
    keys = redis_cli("--scan", "--pattern", f"rag:{collection}:*").splitlines()
    keys = [k for k in keys if k.startswith("rag:")]
    
    if not keys:
        print(f"  {collection}: no keys found")
        continue
    
    for key in keys:
        current_ttl = int(redis_cli("TTL", key) or "-1")
        
        if desired_ttl == 0:
            # Make permanent
            if current_ttl != -1:  # -1 = already persistent
                redis_cli("PERSIST", key)
                persisted += 1
        else:
            # Refresh TTL only if current is shorter than desired or already persistent
            if current_ttl == -1:
                # Already persistent, leave it
                pass
            elif current_ttl < desired_ttl:
                redis_cli("EXPIRE", key, str(desired_ttl))
                refreshed += 1
        
        total += 1

print(f"\nDone: {total} keys scanned, {persisted} persisted (TTL removed), {refreshed} TTLs refreshed")