import requests
import re
from typing import Dict, Any, Optional
from util.api_util import _get_gpo_client


import requests
from io import BytesIO

gpo_client = _get_gpo_client()

def _get_CR_Subsections(date:str):
    return ___extractGranules(date)

def _searchAmendmentInCR(amendment: Dict) -> Optional[Dict]:
    """
    Given an amendment descriptor like
        {
            "amendment_type": "samdt",
            "amdt_number": 1593,
            "submittedDate": "2020-06-08",
            "congress": "116"
        }
    return the same dict plus a new key ``text`` containing the full
    amendment text extracted from the Congressional Record.
    Returns ``None`` if the amendment or its text cannot be located.
    Only Senate amendments are supported for now.
    """

    amendment = {
        "congress": amendment["congress"],
        "amdt_number": amendment["amdt_number"],
        "submittedDate": amendment["submittedDate"][:10],
        "chamber": amendment["amendment_type"]
    }
    # 1.  Download the “TEXT OF AMENDMENTS” block for that day
    full_block = __getAmendmentTextFromCR(amendment)
    if full_block is None:                       # failed download
        return None

    # 2.  Only Senate amendments implemented
    if amendment["chamber"] == "samdt":
         # 3.  Extract the specific amendment section
        extracted = __extract_senate_amendment(full_block, amendment["amdt_number"])
        if extracted is None:                        # pattern not found
            return None
        # 4.  Return a *copy* so the input dict is not mutated
        result = amendment.copy()
        result["text"] = extracted
        return result
    
    elif amendment["chamber"] == "hamdt":
        raise NotImplementedError("House amendments (hamdt) not yet supported.")

    return None

   


# ────────────────────────────────────────────────────────────────
# Private helpers -----------------------------------------------
# ────────────────────────────────────────────────────────────────
def __extract_senate_amendment(text: str, number: int) -> Optional[str]:
    """
    Pulls the section that starts with  'SA <number>.'  (case-insensitive,
    tolerant of leading spaces and of an optional dot after 'SA') and ends
    just *before* the next 'SA <other-number>.' header or the end of the
    document.
    """
    num = str(number).lstrip("0")                          # normalise
    # If text is bytes, decode to string
    if isinstance(text, bytes):
        text = text.decode('utf-8', errors='replace')
    print(text[:2000])
    # Start pattern - anchored to the beginning of a line
    start_re = re.compile(rf"(?m)^[ \t]*SA\.?[ \t]+{num}\b.*$", re.IGNORECASE)
    m_start   = start_re.search(text)
    if not m_start:
        return None                                        # not found

    # End pattern – the *next* amendment header after the start
    end_re   = re.compile(r"(?m)^[ \t]*SA\.?[ \t]+\d+\b.*$", re.IGNORECASE)
    m_end    = end_re.search(text, pos=m_start.end())
    end_idx  = m_end.start() if m_end else len(text)       # until next header
    final_text =  text[m_start.start():end_idx].strip()
    print(final_text)
    return final_text

    
def __getAmendmentTextFromCR(amendment:dict) -> str | None:

    date = amendment["submittedDate"]

    data = ___extractGranules(date)
    house_granules, senate_granules = ___splitGranules(data["granules"])

    if amendment["chamber"] == "samdt":

        for sgran in senate_granules:

            if sgran["title"] == "TEXT OF AMENDMENTS":
                link = sgran["granuleLink"]
                link = re.sub(r'/summary$', r'/htm', link)
                link = re.sub(r'^https://api\.govinfo\.gov', '', link)
                text, _ = gpo_client.get(link)
                # If text is bytes, decode to string
                if isinstance(text, bytes):
                    text = text.decode('utf-8', errors='replace')
                return text
    
    elif amendment["chamber"] == "hamdt":
        raise NotImplementedError

    return None

def ___extractGranules(date:str):

    """
    Format of date: YYYY-MM-DD
    """

    year, month, day = date[:4], date[5:7], date[8:10]
    data, _ = gpo_client.get(f"/packages/CREC-{year}-{month}-{day}/granules")
    return data

def ___splitGranules(granules):

    house_granules = []
    senate_granules = []

    for gran in granules:
        chamber = gran["granuleClass"]

        if chamber == "HOUSE":
            house_granules.append(gran)
        
        elif chamber == "SENATE":
            senate_granules.append(gran)
    
    return house_granules, senate_granules
