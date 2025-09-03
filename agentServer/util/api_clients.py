"""
API Client Utilities
Handles creation and configuration of external API clients (Congress.gov, GPO, OpenAI, etc.)
"""

from openai import AsyncOpenAI
from .cdg_client import CDGClient, GPOClient
from .config_utils import _get_key


def get_openai_client() -> AsyncOpenAI:
    """
    Create and configure OpenAI client with API key from secrets.
    
    Returns:
        Configured AsyncOpenAI client
    """
    openai_key = _get_key("OPENAI_API_KEY")
    return AsyncOpenAI(api_key=openai_key)


def get_cdg_client() -> CDGClient:
    """
    Create and configure Congress.gov API client.
    
    Returns:
        Configured CDGClient instance
    """
    # Note: Congress API key would be extracted from secrets if needed
    # For now, using the client as-is based on current implementation
    try:
        import configparser
        import os
        
        # Try to get Congress API key from secrets
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config = configparser.ConfigParser()
        
        # Look for secrets file
        for i in range(4):
            secrets_path = os.path.join(script_dir, ".." + i*"/..", "secrets.ini")
            if os.path.exists(secrets_path):
                config.read(secrets_path)
                try:
                    congress_key = config["API_KEYS"]["CONGRESS_API_KEY"]
                    return CDGClient(api_key=congress_key)
                except KeyError:
                    break
        
        # Fallback to client without key if needed
        return CDGClient(api_key="")
        
    except Exception:
        # Fallback for any configuration issues
        return CDGClient(api_key="")


def get_gpo_client() -> GPOClient:
    """
    Create and configure GPO (Government Publishing Office) API client.
    
    Returns:
        Configured GPOClient instance
    """
    try:
        import configparser
        import os
        
        # Try to get GPO API key from secrets
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config = configparser.ConfigParser()
        
        # Look for secrets file
        for i in range(4):
            secrets_path = os.path.join(script_dir, ".." + i*"/..", "secrets.ini")
            if os.path.exists(secrets_path):
                config.read(secrets_path)
                try:
                    gpo_key = config["API_KEYS"]["GPO_API_KEY"]
                    return GPOClient(api_key=gpo_key)
                except KeyError:
                    break
        
        # Fallback to client without key if needed
        return GPOClient(api_key="")
        
    except Exception:
        # Fallback for any configuration issues
        return GPOClient(api_key="")