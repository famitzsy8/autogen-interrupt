"""
Data Processing Utilities
Handles parsing, text extraction, and data transformation tasks
"""

from bs4 import BeautifulSoup
from .api_clients import get_cdg_client

import xml.etree.ElementTree as ET

import requests
import os


local_path = os.path.dirname(os.path.abspath(__file__))

# Get CDG client instance
cdg_client = get_cdg_client()

def parse_xml(xml_string: str) -> ET.Element:
    """Parse XML string into ElementTree root element."""
    return ET.fromstring(xml_string)

def extract_htm_pdf_from_xml(root: ET.Element, is_amendment=False, is_hearing=False) -> dict:
    """
    Extract HTML and PDF URLs from XML text versions and return structured data.
    
    Args:
        root: XML root element from Congress API response
        is_amendment: Whether this is amendment data
        is_hearing: Whether this is hearing data
        
    Returns:
        Dictionary with text versions, URLs, and extracted text
    """
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
            urls["text_version"] = parse_text_version(pdf_url)

        urls["pdf_url"] = pdf_url
        urls["text"] = extract_text_from_html_url(htm_url)

    return urls


def extract_text_from_html_url(url: str) -> str:
    """
    Download and extract clean text from HTML URL.
    
    Args:
        url: URL to HTML document
        
    Returns:
        Cleaned text content
    """
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