import os
import json

local_path = os.path.dirname(os.path.abspath(__file__))

def _get_description_for_function(function_name: str) -> str:

    path = f'{local_path}/../../data/descriptions/mcp_descriptions.json'

    with open(path, 'r') as f:
        descriptions = json.load(f)

    return descriptions.get(function_name, "")