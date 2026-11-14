FROM python:3.12-slim

# Install system dependencies, git, curl, and GitHub CLI (gh)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    gnupg \
    build-essential \
    && mkdir -p -m 755 /etc/apt/keyrings \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
    && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy AEW source and install
COPY . /workspace/aew-src
RUN pip install --no-cache-dir /workspace/aew-src

# Expose Web Cockpit
EXPOSE 8000

# Set default command
CMD ["aew", "serve", "--host", "0.0.0.0", "--port", "8000"]
