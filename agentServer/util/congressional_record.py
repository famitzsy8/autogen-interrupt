"""
Congressional Record Utilities
Handles searching and extracting text from Congressional Record documents
"""

import re
from typing import Dict, Optional
from .api_clients import get_gpo_client

# Get GPO client instance
gpo_client = get_gpo_client()


def search_amendment_in_cr(amendment: Dict) -> Optional[Dict]:
    """
    Search for amendment text in Congressional Record.
    
    Given an amendment descriptor like:
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
    
    Args:
        amendment: Amendment metadata dictionary
        
    Returns:
        Amendment dict with text field added, or None if not found
    """
    amendment = {
        "congress": amendment["congress"],
        "amdt_number": amendment["amdt_number"],
        "submittedDate": amendment["submittedDate"][:10],
        "chamber": amendment["amendment_type"]
    }
    
    # 1. Download the "TEXT OF AMENDMENTS" block for that day
    full_block = get_amendment_text_from_cr(amendment)
    if full_block is None:  # failed download
        return None

    # 2. Only Senate amendments implemented
    if amendment["chamber"] == "samdt":
        # 3. Extract the specific amendment section
        extracted = extract_senate_amendment(full_block, amendment["amdt_number"])
        if extracted is None:  # pattern not found
            return None
        # 4. Return a *copy* so the input dict is not mutated
        result = amendment.copy()
        result["text"] = extracted
        return result
    
    elif amendment["chamber"] == "hamdt":
        raise NotImplementedError("House amendments (hamdt) not yet supported.")

    return None


def extract_senate_amendment(text: str, number: int) -> Optional[str]:
    """
    Extract specific Senate amendment text from Congressional Record.
    
    Pulls the section that starts with 'SA <number>.' (case-insensitive,
    tolerant of leading spaces and of an optional dot after 'SA') and ends
    just *before* the next 'SA <other-number>.' header or the end of the
    document.
    
    Args:
        text: Full Congressional Record text
        number: Amendment number to extract
        
    Returns:
        Amendment text if found, None otherwise
    """
    num = str(number).lstrip("0")  # normalise
    # If text is bytes, decode to string
    if isinstance(text, bytes):
        text = text.decode('utf-8', errors='replace')
        
    # Start pattern - anchored to the beginning of a line
    start_re = re.compile(rf"(?m)^[ \t]*SA\.?[ \t]+{num}\b.*$", re.IGNORECASE)
    m_start = start_re.search(text)
    if not m_start:
        return None  # not found

    # End pattern – the *next* amendment header after the start
    end_re = re.compile(r"(?m)^[ \t]*SA\.?[ \t]+\d+\b.*$", re.IGNORECASE)
    m_end = end_re.search(text, pos=m_start.end())
    end_idx = m_end.start() if m_end else len(text)  # until next header
    final_text = text[m_start.start():end_idx].strip()

    return final_text


def get_amendment_text_from_cr(amendment: dict) -> str | None:
    """
    Get the right granule to search for amendment text in Congressional Record.
    
    Args:
        amendment: Amendment metadata with submittedDate and chamber
        
    Returns:
        Congressional Record text for amendment search, or None if not found
    """
    date = amendment["submittedDate"]

    data = extract_granules(date)
    house_granules, senate_granules = split_granules(data["granules"])

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


def extract_granules(date: str):
    """
    Get granules for Congressional Record of a given day.
    
    Args:
        date: Date in YYYY-MM-DD format
        
    Returns:
        Granules data from GPO API
    """
    year, month, day = date[:4], date[5:7], date[8:10]
    data, _ = gpo_client.get(f"/packages/CREC-{year}-{month}-{day}/granules")
    return data


def split_granules(granules):
    """
    Split granules into House and Senate categories.
    
    Args:
        granules: List of granule objects
        
    Returns:
        Tuple of (house_granules, senate_granules)
    """
    house_granules = []
    senate_granules = []

    for gran in granules:
        chamber = gran["granuleClass"]

        if chamber == "HOUSE":
            house_granules.append(gran)
        
        elif chamber == "SENATE":
            senate_granules.append(gran)
    
    return house_granules, senate_granules