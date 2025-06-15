# !/03_Code/congressMCP/.ba-venv/bin/python
# util.py

import configparser, os
from openai import AsyncOpenAI
from cdg_client import CDGClient

def __get_api_keys(path="../secrets.ini"):
    config = configparser.ConfigParser()
    if not os.path.exists(path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute path to other.txt
        other_path = os.path.join(script_dir, "..", "secrets.ini")
        if not os.path.exists(other_path):
            raise FileNotFoundError(f"Secrets file not found at: {other_path}, because the script was called from {os.getcwd()}")
        path = other_path
    config.read(path)

    try:
        congress_key = config["API_KEYS"]["CONGRESS_API_KEY"]
        openai_key = config["API_KEYS"]["OPENAI_API_KEY"]
    except KeyError as e:
        raise KeyError(f"Missing expected key in secrets.ini: {e}")

    return congress_key, openai_key

def _get_cdg_client():
    congress_key, openai_key = __get_api_keys()

    cdg_client = CDGClient(api_key=congress_key, response_format="xml")

    return cdg_client

def _get_oai_client():
    congress_key, openai_key = __get_api_keys()

    oai_client = AsyncOpenAI(api_key=openai_key)

    return oai_client