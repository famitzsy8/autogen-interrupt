import os
import json
import tiktoken

# Depending where we are calling the script that uses the MCP functions, we need to adapt
# the path dynamically 
def _craft_adapted_path(rel_path:str) -> str:

    if not os.path.exists(rel_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute path to other.txt
        other_paths = [os.path.join(script_dir, ".." + i*"/..", rel_path) for i in range(0, 4)]

        for other_path in other_paths:
            if os.path.exists(other_path):
                return other_path
                
        raise FileNotFoundError(f"Secrets file not found at: {other_path}, because the script was called from {os.getcwd()}")

    return rel_path

# Gets us the functional descriptions for the MCP functions that the agents will use to choose the tools
def _get_description_for_function(func_name: str, path: str = None) -> str:

    if path is None:
        path = _craft_adapted_path('data/mcp_descriptions.json')

    with open(path, 'r') as f:
        descriptions = json.load(f)

    return descriptions.get(func_name, "")

def get_token_encoder():
    try:
        _ENCODER = tiktoken.get_encoding("cl100k_base")
    except ModuleNotFoundError:
        class _DummyEncoder:  # pylint: disable=too-few-public-methods
            def encode(self, text: str):  # noqa: D401
                return text.split()

            def decode(self, tokens):  # noqa: D401
                return " ".join(tokens)

        _ENCODER = _DummyEncoder()

    return _ENCODER