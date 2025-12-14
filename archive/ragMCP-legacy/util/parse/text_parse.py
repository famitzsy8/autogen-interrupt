import re
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET


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

# Takes a root of an XML tree response from a text call (amendments, bills or committee hearings) and returns a dictionary with all the text versions
def _extract_htm_pdf_from_xml(root: ET.Element, is_amendment=False, is_hearing=False) -> dict:            

    pdf_urls = []
    html_urls = []

    for text_version in root.findall(".//textVersions/item"):
        for format_item in text_version.findall(".//formats/item"):

            type_text = format_item.findtext("type", "").strip().lower()
            url_text = format_item.findtext("url", "").strip()

            if "pdf" in type_text:
                pdf_urls.append(url_text)

            elif "formatted text" in type_text or "html" in type_text:
                html_urls.append(url_text)
    urls = {}

    for pdf_url, htm_url in zip(pdf_urls, html_urls):
        # Amendments don't come with text versions
        if not is_amendment:
            urls["text_version"] = __parse_text_version(pdf_url)

        urls["pdf_url"] = pdf_url
        urls["text"] = __extract_text_from_html_url(htm_url)

    return urls

def __extract_text_from_html_url(url: str) -> str:

    response = requests.get(url)
    response.raise_for_status() # raises an exception on HTTP errors

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script/style elements
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    # Get text and collapse whitespace
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

def __parse_text_version(text_url: str):

    try:
        # Check if it is a public law
        if re.search("PLAW-(\d+)publ(\d+)", text_url):
            return BILL_VERSION_MAP["pl"]
        
        text_version = text_url[-7:-4] # ...rds.htm
        if text_version[0] in "12345567890":
            text_version = text_version[1:]
        
        return BILL_VERSION_MAP[text_version]
    except:
        return "No text version information could be found"

def _extract_htm_pdf_from_xml(root: ET.Element, is_amendment=False, is_hearing=False) -> dict:            

    pdf_urls = []
    html_urls = []

    for text_version in root.findall(".//textVersions/item"):
        for format_item in text_version.findall(".//formats/item"):

            type_text = format_item.findtext("type", "").strip().lower()
            url_text = format_item.findtext("url", "").strip()

            if "pdf" in type_text:
                pdf_urls.append(url_text)

            elif "formatted text" in type_text or "html" in type_text:
                html_urls.append(url_text)
    urls = {}

    for pdf_url, htm_url in zip(pdf_urls, html_urls):
        # Amendments don't come with text versions
        if not is_amendment:
            urls["text_version"] = __parse_text_version(pdf_url)

        urls["pdf_url"] = pdf_url
        urls["text"] = __extract_text_from_html_url(htm_url)

    return urls