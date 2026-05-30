FROM python:3.11-slim

WORKDIR /app

# System deps + solc + Foundry (consolidated for smaller layer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl git ca-certificates && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Solidity compiler (kept — used by contract scanners)
RUN curl -sL https://github.com/ethereum/solidity/releases/download/v0.8.26/solc-static-linux -o /usr/local/bin/solc && \
    chmod +x /usr/local/bin/solc

# Foundry (cast, forge) — EVM contract analysis
RUN curl -sL https://foundry.paradigm.xyz | bash && \
    export PATH="$HOME/.foundry/bin:$PATH" && \
    foundryup

# Python deps (ordered for layer caching: requirements first, then app)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir slither-analyzer && \
    rm -rf /root/.cache/pip

# Copy app (HF models excluded via .dockerignore — they download at runtime)
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "-u", "main.py"]
