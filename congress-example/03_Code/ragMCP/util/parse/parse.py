from util.clients.client import _get_cdg_client

import xml.etree.ElementTree as ET
from typing import Any
import ast

parse_xml = lambda x: ET.fromstring(x)
cdg_client = _get_cdg_client()


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
            print(e)
            raise Exception(f"You have passed a congress index object that doesn't match the path template\n Congress index: {congress_index}\n Path template: {path_template}")

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