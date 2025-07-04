# Shared helper
from api_util import _get_cdg_client
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
import re, json
from math import log10
from other_util import _craft_adapted_path
import yaml


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

def _call_and_parse(congress_index: dict, path_template: str, params={}):
    """
    Helper function to call the Congress API and parse XML root.
    path_template is like "bill/{congress}/{bill_type}/{bill_number}/actions"
    """
    path = path_template.format(**congress_index)
    print(f"\n\n PATH USED: {path}")
    data, _ = cdg_client.get(endpoint=path, params=params)
    return parse_xml(data)

def _parse_oai_json_response(oai_response:str) -> dict:
    """
    Helper function to orchestrate the parsing of an OpenAI model's response into a JSON object
    """
    content = oai_response.choices[0].message.content.strip()

    try:
        parsed = __parse_json_response(content)
    except json.JSONDecodeError as e:
        # If the model responded with something that isn’t valid JSON, raise an error
        raise ValueError(f"GPT-4o response was not valid JSON:\n{content}") from e

    return parsed

def _parse_roll_call_number_house(roll:int):
    return "0"*(2 - int(log10(roll))) + str(roll)

   
def _extract_htm_pdf_from_xml(root: ET.Element, is_amendment=False) -> dict:
    """
    A helper function that takes a root of an XML element tree and returns all the text versions of a bill or of an amendment to the bill.
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
    print(pdf_urls, html_urls)
    for pdf_url, htm_url in zip(pdf_urls, html_urls):
        if not is_amendment:
            urls["text_version"] = __parse_text_version(pdf_url)
        urls["pdf_url"] = pdf_url
        urls["text"] = __extract_text_from_html_url(htm_url)

    return urls

def __parse_json_response(text: str):
    """
    Find and parse the first JSON object in `text`, handling cases like:
      • Raw JSON: {"a":1}
      • Fenced JSON: ```json\n{...}\n```
      • Code-fenced without language: ```\n{...}\n```
      • JSON embedded in extra text

    Returns the parsed Python object (dict/list/etc.), or raises ValueError.
    """
    # 1) Try fenced blocks first
    fence_re = re.compile(
        r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```",
        re.IGNORECASE | re.DOTALL
    )
    m = fence_re.search(text)
    if m:
        candidate = m.group(1)
        return json.loads(candidate)

    # 2) Fallback: find the first {...} or [...] balanced block
    #    Scan from first brace, keep a stack count until matching close.
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        if start != -1:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == start_char:
                    depth += 1
                elif text[i] == end_char:
                    depth -= 1
                # when we've closed all opened braces/brackets
                if depth == 0:
                    candidate = text[start:i+1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break
    raise ValueError("No valid JSON object found in the input text.")

def __parse_text_version(text_url: str):
    """
    An internal utility function that parses the text version that is hidden inside the filename of the text files
    """
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

def __extract_text_from_html_url(url: str) -> str:
    
    """
    An internal utility function that extracts the bill text from an HTM url
    """

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


def _get_committee_code(name: str) -> dict:
    debug_messages = []
    path = _craft_adapted_path("data/committees_standing.yaml")
    debug_messages.append(f"Loading YAML from: {path}")

    with open(path, "r") as f:
        committees = yaml.safe_load(f)
    raw = name.strip()
    debug_messages.append(f"Raw input: {raw}")

    if "house" not in raw.lower() and "senate" not in raw.lower():
        debug_messages.append("Input is missing 'House' or 'Senate' — cannot determine chamber.")
        return {"committee_code": None, "debug": debug_messages}

    # 1) Subcommittee form
    sub_re = re.compile(
        r"^Subcommittee on (.+) under the (House|Senate) Committee on (.+)$",
        re.IGNORECASE
    )
    m = sub_re.match(raw)
    if m:
        sub_name, chamber, parent_main = m.groups()
        parent_full = f"{chamber} Committee on {parent_main}".strip().lower()
        sub_name = sub_name.strip().lower()
        debug_messages.append(f"Subcommittee detected: parent='{parent_full}', sub='{sub_name}'")

        for c in committees:
            if c.get("name", "").strip().lower() == parent_full:
                parent_id = c.get("thomas_id")
                debug_messages.append(f"Parent ID found: {parent_id}")
                for sub in c.get("subcommittees", []):
                    if sub.get("name", "").strip().lower() == sub_name:
                        sub_id = sub.get("thomas_id")
                        code = f"{parent_id}{sub_id}"
                        debug_messages.append(f"Subcommittee ID found: {sub_id} -> code: {code}")
                        return {"committee_code": code, "debug": debug_messages}
        debug_messages.append("Parent committee or subcommittee not found.")
        return {"committee_code": None, "debug": debug_messages}

    # 2) Main committee form
    main_re = re.compile(r"^(House|Senate) Committee on (.+)$", re.IGNORECASE)
    m = main_re.match(raw)
    if m:
        chamber, main_body = m.groups()
        full = f"{chamber} Committee on {main_body}".strip().lower()
        debug_messages.append(f"Main committee detected: {full}")
        for c in committees:
            if c.get("name", "").strip().lower() == full:
                base_id = c.get("thomas_id")
                code = f"{base_id}01"
                debug_messages.append(f"Committee code found: {code}")
                return {"committee_code": code, "debug": debug_messages}
        debug_messages.append("Main committee not found.")
        return {"committee_code": None, "debug": debug_messages}

    debug_messages.append("Input did not match any known committee format.")
    return {"committee_code": None, "debug": debug_messages}
