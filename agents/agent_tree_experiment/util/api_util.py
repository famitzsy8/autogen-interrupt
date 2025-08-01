import configparser, os
from openai import AsyncOpenAI
from util.cdg_client import CDGClient, GPOClient
from google import genai

# Searches the secrets.ini file and returns the API keys for GoogleAI and OpenAI
def __get_api_keys(path="../secrets.ini"):
    config = configparser.ConfigParser()
    if not os.path.exists(path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute path to other.txt
        other_paths = [os.path.join(script_dir, ".." + i*"/..", "secrets.ini") for i in range(0, 4)]

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

    return openai_key, gai_key

