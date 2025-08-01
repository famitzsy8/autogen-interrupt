# 
# util.py

import configparser, os
from openai import AsyncOpenAI
from util.cdg_client import CDGClient, GPOClient
from google import genai


def __get_api_keys(path="../secrets.ini"):
    config = configparser.ConfigParser()
    if not os.path.exists(path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute path to other.txt
        other_paths = [os.path.join(script_dir, "..", "secrets.ini"), os.path.join(script_dir, "..", "..", "secrets.ini")]
        for other_path in other_paths:
            if os.path.exists(other_path):
                config.read(other_path)
                return ___fetch_keys_from_path(config=config)
        raise FileNotFoundError(f"Secrets file not found at: {other_path}, because the script was called from {os.getcwd()}")


def ___fetch_keys_from_path(config):
    try:
        congress_key = config["API_KEYS"]["CONGRESS_API_KEY"]
        openai_key = config["API_KEYS"]["OPENAI_API_KEY"]
        gai_key = config["API_KEYS"]["GOOGLE_API_KEY"]
        gpo_key = config["API_KEYS"]["GPO_API_KEY"]
    except KeyError as e:
        raise KeyError(f"Missing expected key in secrets.ini: {e}")

    return congress_key, openai_key, gai_key, gpo_key

    

def _get_cdg_client():
    congress_key, _, _, _ = __get_api_keys()

    cdg_client = CDGClient(api_key=congress_key, response_format="xml")

    return cdg_client

def _get_oai_client():
    _, openai_key, _, _ = __get_api_keys()

    oai_client = AsyncOpenAI(api_key=openai_key)

    return oai_client

def _get_gai_client():
    _, _, gai_key, _ = __get_api_keys()
    gai_client = genai.Client(api_key=gai_key)
    return gai_client

def _get_gpo_client():
    _, _, _, gpo_key = __get_api_keys()
    gpo_client = GPOClient(api_key=gpo_key)
    return gpo_client