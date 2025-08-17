import re, json
import yaml
import requests
from math import log10

import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from util.other_util import _craft_adapted_path
from util.api_util import _get_cdg_client
from typing import List
from util.other_util import get_token_encoder

from typing import Any

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

# Takes a congress index and a path template that is 
def _call_and_parse(congress_index: dict, path_template: str, params={}, multiple_pages=False):

    all_roots = []
    offset = 0
    limit = 250
    key = ""

    # Since the Congress API is paginated with a limit of 250, we will need to loop through the pages
    while True:

        params["offset"] = offset
        try:
            path = path_template.format(**congress_index)
            data, _ = cdg_client.get(endpoint=path, params=params)
            root = parse_xml(data)

            if not multiple_pages:
                return root
            
            key = root[0].tag
            elements = root.findall(f".//{key}/item")
            all_roots.append(root)

            if len(elements) < limit:
                break
        
            offset += limit

            return all_roots
        except Exception as e:
            raise Exception(f"You have passed a congress index object that doesn't match the path template\n Congress index: {congress_index}\n Path template: {path_template}")

# Parses a (pure JSON)response from the OpenAI model 
def _parse_oai_json_response(oai_response:str) -> dict:

    content = oai_response.choices[0].message.content.strip()

    try:
        parsed = __parse_json_response(content)
    except json.JSONDecodeError as e:
        # If the model responded with something that isn’t valid JSON, raise an error
        raise ValueError(f"GPT-4o response was not valid JSON:\n{content}") from e

    return parsed

# A function that takes a roll call number and makes sure it is three digits long, such that we
# can index it to fetch the votes from the House Clerk's website
def _parse_roll_call_number_house(roll:int):

    return "0"*(2 - int(log10(roll))) + str(roll)

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

# Extracts all the unique raw text URLs (.htm) that correspond to the endpoint where we can find the
# text of a committee report
def _parse_committee_report_text_links(text_items):

    seen_htm = set()
    parsed = []

    for item in text_items:

        url = (item.findtext('url') or '').strip()
        type = (item.findtext('type') or '').strip()
        is_errata = (item.findtext('isErrata') or '').strip().lower() in ('y', 'true')

        if url.endswith('.pdf'):
            continue

        elif url.endswith('.htm') or url.endswith('.html'):
            if url not in seen_htm:

                seen_htm.add(url)
                text = __extract_text_from_html_url(url)
                parsed.append({'url': url, 'type': type, 'isErrata': is_errata, 'text': text})

    return parsed

# The core logic for parsing the JSON response from the OpenAI model
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

# An internal utility function that helps us extract the text version type from the filename of the text file
# See BILL_VERSION_MAP at the top of this file to see what is meant by the text version type
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

# Internal utility function that makes the HTTP request to get the bill text from a.htm URL
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

# Takes a committee_name and searches the standing committees YAML file (in the ../data directory)
# to find the committee code that corresponds to the committee name
# We can then use this code to fetch the committee roster from the other files
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


# this function is used to compress a list of numbers into a string of ranges
# e.g. [1, 2, 3, 5, 6, 7, 8, 10] -> "1-3, 5-8, 10"
def _compress_numbers(nums: List[int]) -> str:
    if not nums: return ""
    nums = sorted(set(nums))
    ranges, start = [], nums[0]
    for i in range(1, len(nums)):
        if nums[i] != nums[i-1] + 1:
            ranges.append(f"{start}-{nums[i-1]}" if start != nums[i-1] else f"{start}")
            start = nums[i]
    ranges.append(f"{start}-{nums[-1]}" if start != nums[-1] else f"{start}")
    return ", ".join(ranges)

_ENCODER = get_token_encoder()

def _token_count(text: str) -> int:
    return len(_ENCODER.encode(text))

# removes the text between <DELETED> and </DELETED> tags that indicate overwritten text in a bill
def remove_deleted_text(text: str) -> str:
    return re.sub(r"<DELETED>.*?</DELETED>", "", text, flags=re.DOTALL)

# returns a list of text chunks that are no more than tokens_per_chunk tokens long, with specified overlap (in tokens)
def _fixed_size_chunk(text: str, tokens_per_chunk: int, overlap: int = 0) -> List[str]:
    # Normalize inputs to integers and support fractional overlaps (e.g., 0.15)
    if tokens_per_chunk <= 0:
        raise ValueError("tokens_per_chunk must be positive")

    # Allow overlap to be specified as a fraction (<1) or absolute token count (>=1)
    if isinstance(overlap, float) and 0 < overlap < 1:
        overlap_tokens = int(tokens_per_chunk * overlap)
    else:
        overlap_tokens = int(overlap)

    tokens_per_chunk = int(tokens_per_chunk)

    # Ensure overlap is within valid bounds
    if overlap_tokens >= tokens_per_chunk:
        overlap_tokens = max(0, tokens_per_chunk - 1)

    tokens = _ENCODER.encode(text)
    chunks: List[str] = []
    i = 0
    step = max(1, tokens_per_chunk - overlap_tokens)
    while i < len(tokens):
        chunk = tokens[i : i + tokens_per_chunk]
        chunks.append(_ENCODER.decode(chunk))
        if i + tokens_per_chunk >= len(tokens):
            break
        i += step
    return chunks


def _parse_congress_index_from_args(args: Any) -> dict | None:
    """
    Parses a variety of messy agent inputs to extract the core congress_index dictionary.
    Handles nested wrappers and stringified dictionaries.
    """
    if not isinstance(args, (dict, str)):
        return None

    # If args is a string, try to parse it into a dict.
    # Agents often incorrectly pass stringified dicts.
    if isinstance(args, str):
        try:
            args = ast.literal_eval(args)
            if not isinstance(args, dict):
                return None
        except (ValueError, SyntaxError):
            return None # Not a stringified dict.

    # Now `args` is guaranteed to be a dict.
    # Check if the payload is at the top level.
    # This is the base case for the recursion.
    if "congress" in args and ("bill_type" in args or "reportType" in args or "chamber" in args):
         return args

    # If not, check for common wrapper keys and recurse.
    for key in ["congress_index", "self"]:
        if key in args:
            # Recursively call with the value of the wrapper key
            return _parse_congress_index_from_args(args[key])

    return None