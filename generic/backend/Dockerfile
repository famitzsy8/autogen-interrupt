FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Copy autogen extensions from local directory
COPY autogen-extension /tmp/autogen-extension

# Replace installed autogen packages with custom extensions
RUN SITE_PACKAGES=$(python -c "import sysconfig; print(sysconfig.get_paths()['purelib'])") && \
    rm -rf "${SITE_PACKAGES}/autogen_core" "${SITE_PACKAGES}/autogen_agentchat" && \
    cp -R /tmp/autogen-extension/autogen_core "$SITE_PACKAGES/" && \
    cp -R /tmp/autogen-extension/autogen_agentchat "$SITE_PACKAGES/" && \
    cp -R /tmp/autogen-extension/autogen_core-0.7.4.dist-info "$SITE_PACKAGES/" && \
    cp -R /tmp/autogen-extension/autogen_agentchat-0.7.4.dist-info "$SITE_PACKAGES/" && \
    rm -rf /tmp/autogen-extension

# Copy application code
COPY . .

EXPOSE 8001

CMD ["tail", "-f", "/dev/null"]