from util.parse.parse import _call_and_parse, _parse_congress_index_from_args
from util.parse.text_parse import _extract_htm_pdf_from_xml

def extractBillText(congress_index:dict) -> dict:
    debug = []
    parsed_index = _parse_congress_index_from_args(congress_index)
    if not parsed_index:
        debug.append(f"Could not parse congress_index from input: {congress_index}")
        return {"text_versions": [], "debug": debug}

    endpoint = "bill/{congress}/{bill_type}/{bill_number}/text"
    root = _call_and_parse(parsed_index, endpoint)
    urls = _extract_htm_pdf_from_xml(root)
    debug.append(f"Extracted {len(urls)} text versions for bill {parsed_index}")
    return {"text_versions": urls, "debug": debug}

def getBillSummary(congress_index:dict) -> dict:
    debug = []
    parsed_index = _parse_congress_index_from_args(congress_index)
    if not parsed_index:
        debug.append(f"Could not parse congress_index from input: {congress_index}")
        return {"summary": None, "debug": debug}
    
    endpoint = "bill/{congress}/{bill_type}/{bill_number}/summaries"
    root = _call_and_parse(parsed_index, endpoint)

    summaries = []
    for summary_elem in root.findall('.//summaries/summary'):
        version_code = summary_elem.findtext('versionCode')
        action_date = summary_elem.findtext('actionDate')
        action_desc = summary_elem.findtext('actionDesc')
        update_date = summary_elem.findtext('updateDate')
        # The summary text is inside <cdata><text>
        text_elem = summary_elem.find('.//cdata/text')
        summary_text = text_elem.text if text_elem is not None else None

        summaries.append({
            "versionCode": version_code,
            "actionDate": action_date,
            "actionDesc": action_desc,
            "updateDate": update_date,
            "summary": summary_text
        })
    debug.append(f"Extracted {len(summaries)} summaries for bill {parsed_index}")
    return {"summary": summaries, "debug": debug}

def getCongressMember(bioguideId: str) -> dict:

    endpoint = "member/{bioguideId}"
    root = _call_and_parse({"bioguideId": bioguideId}, endpoint)
    
    debug = []
    
    try:
        first = root.find(".//firstName").text
        last = root.find(".//lastName").text
        middle = root.findtext(".//directOrderName")
        full_name = middle if middle else f"{first} {last}"
        debug.append(f"Parsed full name: {full_name}")
    except Exception as e:
        full_name = None
        debug.append(f"Failed to parse name: {e}")

    try:
        state = root.findtext(".//state")
        debug.append(f"Parsed state: {state}")
    except Exception as e:
        state = None
        debug.append(f"Failed to parse state: {e}")
    
    try:
        state_code = root.find(".//terms/item/stateCode").text
        debug.append(f"Parsed stateCode: {state_code}")
    except Exception as e:
        state_code = None
        debug.append(f"Failed to parse stateCode: {e}")
    try:
        party = root.find(".//partyHistory/item/partyName").text
        debug.append(f"Parsed party: {party}")
    except Exception as e:
        party = None
        debug.append(f"Failed to parse party: {e}")

    try:
        congress_items = root.findall(".//terms/item/congress")
        congresses = sorted({int(c.text) for c in congress_items})
        debug.append(f"Parsed congress sessions: {congresses}")
    except Exception as e:
        congresses = []
        debug.append(f"Failed to parse congress sessions: {e}")
    
    return {
        "fullName": full_name,
        "state": state,
        "stateCode": state_code,
        "party": party,
        "congressesServed": congresses,
        "debug": debug
    }