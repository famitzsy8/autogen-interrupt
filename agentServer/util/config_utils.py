"""
Configuration and File Path Utilities
Handles configuration file access, API keys, and path resolution
"""

import configparser
import os
import json
from typing import Tuple


def craft_adapted_path(rel_path: str) -> str:
    """
    Dynamically adapt relative paths based on current script location.
    
    Args:
        rel_path: Relative path to the target file
        
    Returns:
        Absolute path to the file
        
    Raises:
        FileNotFoundError: If file cannot be found in any expected location
    """
    if not os.path.exists(rel_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute path by checking parent directories
        other_paths = [os.path.join(script_dir, ".." + i*"/..", rel_path) for i in range(0, 4)]

        for other_path in other_paths:
            if os.path.exists(other_path):
                return other_path
                
        raise FileNotFoundError(f"File not found at: {rel_path}, searched from {os.getcwd()}")

    return rel_path


cfg = configparser.ConfigParser()
cfg.read(os.environ.get("SECRETS_INI_FILE", "/run/secrets/secrets.ini"))

def _get_key(key_name: str):
    if key_name not in cfg["API_KEYS"]:
        raise ValueError(f"Key name {key_name} not found in secrets.ini")
    return cfg["API_KEYS"][key_name]


def get_function_description(func_name: str, path: str = None) -> str:
    """
    Get functional descriptions for MCP functions that agents use to choose tools.
    
    Args:
        func_name: Name of the function to get description for
        path: Optional path to descriptions file
        
    Returns:
        Description string for the function, empty string if not found
    """
    if path is None:
        path = craft_adapted_path('../data/mcp_descriptions.json')

    try:
        with open(path, 'r') as f:
            descriptions = json.load(f)
        return descriptions.get(func_name, "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""