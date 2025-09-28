source interrupt-cursor-venv/bin/activate
pip install -r requirements.txt

cp -r autogen-extension/autogen-core interrupt-cursor-venv/lib/python3.13/site-packages/
cp -r autogen-extension/autogen-agentchat interrupt-cursor-venv/lib/python3.13/site-packages/
