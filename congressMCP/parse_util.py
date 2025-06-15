# Shared helper
from api_util import _get_cdg_client
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
import re, json

cdg_client = _get_cdg_client()

parse_xml = lambda x: ET.fromstring(x)

BILL_VERSION_MAP = {
    "ih": "Introduced in House (First draft introduced)",
    "is": "Introduced in Senate (First draft introduced)",
    "eh": "Engrossed in House (Passed by House)",
    "es": "Engrossed in Senate (Passed by Senate)",
    "rds": "Received in Senate (Sent from House to Senate)",
    "res": "Received in House (Sent from Senate to House)",
    "enr": "Enrolled (Passed both chambers)",
    "pcs": "Placed on Calendar Senate (Scheduled for action)",
    "rh": "Reported in House (Report from House Committee)",
    "rs": "Reported in Senate (Report from Senate Committee)",
    "pl": "Public Law (Became law - final version)"
}

def _call_and_parse(congress_index: dict, path_template: str):
    """
    Internal utility to call the Congress API and parse XML root.
    path_template is like "bill/{congress}/{bill_type}/{bill_number}/actions"
    """
    path = path_template.format(**congress_index)
    data, _ = cdg_client.get(endpoint=path)
    return parse_xml(data)

def _parse_oai_json_response(oai_response:str) -> dict:
    content = oai_response.choices[0].message.content.strip()
    content = content[7:-3] #  ```json{content}``` 
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        # If the model responded with something that isn’t valid JSON, raise an error
        raise ValueError(f"GPT-4o response was not valid JSON:\n{content}") from e

    return parsed

   
def _extract_htm_pdf_from_xml(root: ET.Element) -> dict:
    pdf_urls = []
    html_urls = []

    for text_version in root.findall(".//textVersions/item"):
        for format_item in text_version.findall(".//formats/item"):
            type_text = format_item.findtext("type", "").strip().lower()
            url_text = format_item.findtext("url", "").strip()

            if "pdf" in type_text:
                pdf_urls.append(url_text)
            elif "formatted text" in type_text:
                html_urls.append(url_text)

    urls = {}

    for pdf_url, htm_url in zip(pdf_urls, html_urls):

        urls["text_version"] = __parse_text_version(pdf_url)
        urls["pdf_url"] = pdf_url
        urls["text"] = __extract_text_from_html_url(htm_url)

    return urls


def __parse_text_version(text_url: str):
    # Check if it is a public law
    if re.search("PLAW-(\d+)publ(\d+)", text_url):
        return BILL_VERSION_MAP["pl"]
    
    text_version = text_url[-7:-4] # ...rds.htm
    if text_version[0] in "12345567890":
        text_version = text_version[1:]
    
    return BILL_VERSION_MAP[text_version]

def __extract_text_from_html_url(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()  # raise exception on HTTP errors

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script/style elements
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    # Get text and collapse whitespace
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
