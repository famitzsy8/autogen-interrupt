#!/usr/bin/env bash
set -euo pipefail

source interrupt-cursor-venv/bin/activate

SITE_PACKAGES=$(python - <<'PY'
import sysconfig
print(sysconfig.get_paths()["purelib"])
PY
)

rm -rf ./autogen-extension/autogen_core ./autogen-extension/autogen_agentchat
rm -rf ./autogen-extension/autogen_core-0.7.4.dist-info ./autogen-extension/autogen_agentchat-0.7.4.dist-info

cp -R "${SITE_PACKAGES}/autogen_core" ./autogen-extension/
cp -R "${SITE_PACKAGES}/autogen_agentchat" ./autogen-extension/
cp -R "${SITE_PACKAGES}/autogen_core-0.7.4.dist-info" ./autogen-extension/
cp -R "${SITE_PACKAGES}/autogen_agentchat-0.7.4.dist-info" ./autogen-extension/