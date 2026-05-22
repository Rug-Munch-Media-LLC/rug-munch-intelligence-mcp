FROM python:3.11-slim

WORKDIR /app

# System deps + solc (Solidity compiler for slither)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl git && \
    rm -rf /var/lib/apt/lists/*

# Install solc (Solidity compiler)
RUN curl -L https://github.com/ethereum/solidity/releases/download/v0.8.26/solc-static-linux -o /usr/local/bin/solc && \
    chmod +x /usr/local/bin/solc

# Install Foundry (cast, forge)
RUN curl -L https://foundry.paradigm.xyz | bash && \
    export PATH="$HOME/.foundry/bin:$PATH" && \
    foundryup

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install slither
RUN pip install --no-cache-dir slither-analyzer

# Copy app
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "-u", "main.py"]
