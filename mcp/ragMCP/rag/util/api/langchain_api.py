import configparser, os

def _get_oai_key():
    config = configparser.ConfigParser()
    path = os.path.join(os.path.dirname(__file__), "..", "secrets.ini")
    config.read(path)
    return config["API_KEYS"]["LANGCHAIN_API_KEY"]
    