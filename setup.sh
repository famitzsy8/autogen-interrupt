#!/usr/bin/env bash
set -euo pipefail

source interrupt-cursor-venv/bin/activate
pip install -r requirements.txt

SITE_PACKAGES=$(python - <<'PY'
import sysconfig
print(sysconfig.get_paths()["purelib"])
PY
)

rm -rf "${SITE_PACKAGES}/autogen_core" "${SITE_PACKAGES}/autogen_agentchat"
cp -R ./autogen-extension/autogen_core "$SITE_PACKAGES/"
cp -R ./autogen-extension/autogen_agentchat "$SITE_PACKAGES/"
cp -R ./autogen-extension/autogen_core-0.7.4.dist-info "$SITE_PACKAGES/"
cp -R ./autogen-extension/autogen_agentchat-0.7.4.dist-info "$SITE_PACKAGES/"