# Python container for agentServer WebSocket service with dependencies
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt* ./

# Install dependencies if requirements.txt exists
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Copy application code
COPY . .

# Expose the WebSocket server port
EXPOSE 8766

# Keep container running for VSCode attachment
CMD ["tail", "-f", "/dev/null"]