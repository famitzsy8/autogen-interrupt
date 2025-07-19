# !/03_Code/congressMCP/.ba-venv/bin/python
# util.py

import configparser, os
from openai import AsyncOpenAI
from google import genai

MODELS = {
    "openai": [
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
        "o3-mini",
        "o1-mini",
        "o1-preview",
        "o1"
    ],
    "meta_llama": [
        "Llama-4-Scout-17B-16E-Instruct-FP8",
        "Llama-4-Maverick-17B-128E-Instruct-FP8",
        "Llama-3.3-70B-Instruct",
        "Llama-3.3-8B-Instruct"
    ],
    "gemini": [
        "2.5-flash-preview-04-17",
        "2.5-pro-preview-05-06",
        "2.0-flash",
        "2.0-flash-lite",
        "1.5-flash",
        "1.5-flash-8B",
        "1.5-pro"
    ]
}


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
        openai_key = config["API_KEYS"]["OPENAI_API_KEY"]
        gai_key = config["API_KEYS"]["GOOGLE_API_KEY"]
    except KeyError as e:
        raise KeyError(f"Missing expected key in secrets.ini: {e}")

    return openai_key, gai_key

def _get_oai_client():
    _, openai_key, _, _ = __get_api_keys()

    oai_client = AsyncOpenAI(api_key=openai_key)

    return oai_client

def _get_gai_client():
    _, _, gai_key, _ = __get_api_keys()
    gai_client = genai.Client(api_key=gai_key)
    return gai_client

