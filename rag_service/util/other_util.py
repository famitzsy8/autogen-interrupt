import os, mcp

def _craft_adapted_path(rel_path:str) -> str:
    """
    This is a function that handles relative path conflicts, when the script is called from different locations.
    Claude Desktop for example calls the script from the root directory
    """
    if not os.path.exists(rel_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute path to other.txt
        other_path = os.path.join(script_dir, rel_path)
        if not os.path.exists(other_path):
            raise FileNotFoundError(f"File not found at: {other_path}, because the script was called from {os.getcwd()}")
        return other_path
    return rel_path

def _get_description_for_function(func_name: str, path: str = None) -> str:
    """
    Helper to retrieve the description string for a given function name from descriptions.json.
    """
    import json
    if path is None:
        path = _craft_adapted_path('../data/mcp_descriptions.json')
    with open(path, 'r') as f:
        descriptions = json.load(f)
    return descriptions.get(func_name, "")


async def _show_tools():
    tools = await mcp.list_tools()
    print(tools)