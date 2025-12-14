# Python container for ragMCP service with dependencies
FROM python:3.11-slim

# Install system dependencies for VS Code Remote attachment
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    git \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt* ./

# Install dependencies if requirements.txt exists
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Copy application code
COPY . .

# Expose the MCP server port
EXPOSE 8083

# Keep container running for VSCode attachment
CMD ["tail", "-f", "/dev/null"]