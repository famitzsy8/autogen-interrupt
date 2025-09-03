"""
Configuration and File Path Utilities
Handles configuration file access, API keys, and path resolution
"""

import configparser
import os


cfg = configparser.ConfigParser()
cfg.read(os.environ.get("SECRETS_INI_FILE", "/run/secrets/secrets.ini"))

def _get_key(key_name: str):
    if key_name not in cfg["API_KEYS"]:
        raise ValueError(f"Key name {key_name} not found in secrets.ini")
    return cfg["API_KEYS"][key_name]


