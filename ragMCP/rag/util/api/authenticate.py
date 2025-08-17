import configparser, os

keys = ["OPENAI_API_KEY", "LANGCHAIN_API_KEY", "GOOGLE_API_KEY", "GPO_API_KEY", "CONGRESS_API_KEY"]

def _get_key(key_name: str):
    if key_name not in keys:
        raise ValueError(f"Key name {key_name} not found in keys")
    config = configparser.ConfigParser()
    path = os.path.join(os.path.dirname(__file__), "..", "secrets.ini")
    config.read(path)
    return config["API_KEYS"][key_name]