from rag.util.api.authenticate import _get_key
from util.clients.gov_client import GPOClient, CDGClient

def _get_cdg_client():
    congress_key = _get_key("CONGRESS_API_KEY")
    cdg_client = CDGClient(api_key=congress_key, response_format="xml")
    return cdg_client

def _get_gpo_client():
    gpo_key = _get_key("GPO_API_KEY")
    gpo_client = GPOClient(api_key=gpo_key)