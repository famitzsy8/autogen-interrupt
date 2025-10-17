#!/usr/bin/env bash
set -euo pipefail

# Ensure we're in the debate-backend directory
cd "$(dirname "$0")"

# Activate the virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Get the site-packages directory
SITE_PACKAGES=$(python - <<'PY'
import sysconfig
print(sysconfig.get_paths()["purelib"])
PY
)

# Path to autogen-extension (relative to project root)
EXTENSION_PATH="../autogen-extension"

# Remove existing autogen packages
rm -rf "${SITE_PACKAGES}/autogen_core" "${SITE_PACKAGES}/autogen_agentchat"

# Copy custom autogen extension
cp -R "${EXTENSION_PATH}/autogen_core" "$SITE_PACKAGES/"
cp -R "${EXTENSION_PATH}/autogen_agentchat" "$SITE_PACKAGES/"
cp -R "${EXTENSION_PATH}/autogen_core-0.7.4.dist-info" "$SITE_PACKAGES/"
cp -R "${EXTENSION_PATH}/autogen_agentchat-0.7.4.dist-info" "$SITE_PACKAGES/"

echo "✓ Debate backend setup complete! Custom autogen extension installed."
