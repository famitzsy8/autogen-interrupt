# !/03_Code/.ba-venv/bin/python
# main.py

import yaml
import re
import requests
import xml.etree.ElementTree as ET

from parse_util import _call_and_parse, _parse_oai_json_response, _extract_htm_pdf_from_xml, _parse_roll_call_number_house, _get_committee_code
from other_util import _craft_adapted_path, _get_description_for_function, _show_tools

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="Congress MCP Server", host="127.0.0.1", port=8080, timeout=30)

@mcp.tool(description=_get_description_for_function("convertLVtoCongress"))
def convertLVtoCongress(lobby_view_bill_id: str) -> dict:

    pattern = r'^(s|hr|sconres|hconres|hjres|sjres)(\d{1,5})-(1\d{2}|200)$'
    match = re.match(pattern, lobby_view_bill_id.lower())
    if not match:
        return None
    bill_type, number, congress = match.groups()

    return {
        "congress": congress,
        "bill_type": bill_type,
        "bill_number": number
    }


@mcp.tool(description=_get_description_for_function("extractBillText"))
def extractBillText(congress_index:dict) -> dict:

    """
    Takes an obtained Congress API Index representing a bill in the format of:
        { "congress": 115, "bill_type": "hjres", "bill_number": 44 }
    
    And returns all the versions of the bill text, in the following format:
        {"text_version": "A short description describing the meaning of the text version", "pdf_url": "An URL that links to the PDF version of the text", "text": "The raw text"}
    """
    
    endpoint = "bill/{congress}/{bill_type}/{bill_number}/text"

    root = _call_and_parse(congress_index, endpoint)
    urls = _extract_htm_pdf_from_xml(root)

    return urls


@mcp.tool(description=_get_description_for_function("getBillCosponsors"))
def getBillCosponsors(congress_index: dict) -> list:

    root = _call_and_parse(congress_index, "bill/{congress}/{bill_type}/{bill_number}/cosponsors")
    return [
        {
            "bioguide_id": item.findtext("bioguideId"),
            "full_name": item.findtext("fullName"),
            "first_name": item.findtext("firstName"),
            "last_name": item.findtext("lastName"),
            "party": item.findtext("party"),
            "state": item.findtext("state"),
            "url": item.findtext("url"),
            "district": item.findtext("district"),
            "sponsorship_date": item.findtext("sponsorshipDate"),
            "is_original_cosponsor": item.findtext("isOriginalCosponsor") == "True",
        }
        for item in root.findall(".//cosponsors/item")
    ]


@mcp.tool(description=_get_description_for_function("getBillCommittees"))
def getBillCommittees(congress_index: dict) -> dict:

    root = _call_and_parse(congress_index, "bill/{congress}/{bill_type}/{bill_number}/committees")
    debug = []
    committees = []

    for committee in root.findall(".//committees/item"):
        try:
            c = {
                "system_code": committee.findtext("systemCode"),
                "name": committee.findtext("name"),
                "chamber": committee.findtext("chamber"),
                "type": committee.findtext("type"),
                "activities": [],
                "subcommittees": [],
            }

            # Add committee-level activities
            for act in committee.findall("./activities/item"):
                c["activities"].append({
                    "name": act.findtext("name"),
                    "date": act.findtext("date"),
                })

            # Add subcommittees if any
            for sub in committee.findall("./subcommittees/item"):
                sub_obj = {
                    "system_code": sub.findtext("systemCode"),
                    "name": sub.findtext("name"),
                    "activities": []
                }
                for act in sub.findall("./activities/item"):
                    sub_obj["activities"].append({
                        "name": act.findtext("name"),
                        "date": act.findtext("date"),
                    })
                c["subcommittees"].append(sub_obj)

            committees.append(c)
            debug.append(f"Parsed committee: {c['name']} with {len(c['activities'])} activities")

        except Exception as e:
            debug.append(f"Failed to parse committee: {e}")

    return {
        "committees": committees,
        "debug": debug
    }


@mcp.tool(description=_get_description_for_function("extractBillActions"))
def extractBillActions(congress_index: dict) -> list:

    root = _call_and_parse(congress_index, "bill/{congress}/{bill_type}/{bill_number}/actions")
    return {"actions": [
        {
            "date": item.findtext("actionDate"),
            "text": item.findtext("text"),
            "type": item.findtext("type"),
        }
        for item in root.findall(".//actions/item")
    ]}


@mcp.tool(description=_get_description_for_function("getBillAmendments"))
def getBillAmendments(congress_index:dict) -> dict:

    debug_msgs = []
    debug_msgs.append(f"RAW ARGUMENT: {congress_index!r}")
    if isinstance(congress_index, dict) and 'congress_index' in congress_index:
        congress_index = congress_index['congress_index']
        debug_msgs.append("UNWRAPPED congress_index")
    debug_msgs.append(f"USING ARGUMENT: {congress_index!r}")

    endpoint = "bill/{congress}/{bill_type}/{bill_number}/amendments"

    results = []
    offset = 0
    limit = 250

    while True:
        # build the amendments endpoint with pagination params
        params = {"limit": limit, "offset": offset}
        root = _call_and_parse(congress_index, endpoint, params=params)
        amendments = root.findall('.//amendment')

        # if there are no more amendments, break out
        if not amendments:
            break

        # extract data for each amendment
        for am in amendments:
            results.append({
                'number': am.findtext('number').strip(),
                'congress': int(am.findtext('congress')),
                'type': am.findtext('type'),
                'updateDate': am.findtext('updateDate'),
                'detailUrl': am.findtext('url'),
            })

        # check pagination count to decide if we should continue
        total = int(root.findtext('.//pagination/count', default='0'))
        if offset + limit >= total:
            break

        offset += limit

    return {
        "amendments": results,
        "debug": debug_msgs
    }


@mcp.tool(description=_get_description_for_function("getAmendmentText"))
def getAmendmentText(congress_index: dict) -> dict:

    endpoint = "amendment/{congress}/{bill_type}/{number}/text"
    root = _call_and_parse(congress_index, endpoint)
    # parse_util._extract_htm_pdf_from_xml will walk <textVersions>…<formats>…
    return _extract_htm_pdf_from_xml(root, is_amendment=True)


@mcp.tool(description=_get_description_for_function("getAmendmentActions"))
def getAmendmentActions(congress_index: dict) -> list:

    endpoint = "amendment/{congress}/{type}/{number}/actions"
    root = _call_and_parse(congress_index, endpoint)
    actions = []
    for item in root.findall(".//actions/item"):
        action = {
            "actionDate": item.findtext("actionDate"),
            "text":       item.findtext("text"),
            "type":       item.findtext("type"),
        }
        # optional actionCode
        if item.findtext("actionCode") is not None:
            action["actionCode"] = item.findtext("actionCode")
        # sourceSystem
        ss = item.find("sourceSystem")
        if ss is not None:
            action["sourceSystem"] = {
                "code": ss.findtext("code"),
                "name": ss.findtext("name"),
            }
        # any recordedVotes
        votes = []
        for rv in item.findall(".//recordedVote"):
            votes.append({
                "rollNumber":    rv.findtext("rollNumber"),
                "chamber":       rv.findtext("chamber"),
                "congress":      rv.findtext("congress"),
                "date":          rv.findtext("date"),
                "sessionNumber": rv.findtext("sessionNumber"),
                "url":           rv.findtext("url"),
            })
        if votes:
            action["recordedVotes"] = votes

        actions.append(action)
    return actions

@mcp.tool(description=_get_description_for_function("getAmendmentCoSponsors"))
def getAmendmentCoSponsors(congress_index: dict) -> dict:

    endpoint = "amendment/{congress}/{type}/{number}/cosponsors"
    root = _call_and_parse(congress_index, endpoint)

    # pagination info
    pag = root.find(".//pagination")
    pagination = {
        "count": int(pag.findtext("count", default="0")),
        "countIncludingWithdrawnCosponsors": int(
            pag.findtext("countIncludingWithdrawnCosponsors", default="0")
        ),
    }

    # cosponsor list
    cosponsors = []
    for item in root.findall(".//cosponsors/item"):
        cs = {
            "bioguideId":         item.findtext("bioguideId"),
            "fullName":           item.findtext("fullName"),
            "firstName":          item.findtext("firstName"),
            "lastName":           item.findtext("lastName"),
            "party":              item.findtext("party"),
            "state":              item.findtext("state"),
            "url":                item.findtext("url"),
            "sponsorshipDate":    item.findtext("sponsorshipDate"),
            # convert "True"/"False" → bool
            "isOriginalCosponsor": item.findtext("isOriginalCosponsor") == "True",
        }
        # optional middleName
        if item.findtext("middleName") is not None:
            cs["middleName"] = item.findtext("middleName")
        cosponsors.append(cs)

    return {
        "pagination": pagination,
        "cosponsors": cosponsors
    }

@mcp.tool(description=_get_description_for_function("get_committee_members"))
def get_committee_members(committee_name: str, congress: int, path='data/113_119.yaml') -> dict:

    debug_messages = []

    committee_code, _debug_messages = _get_committee_code(committee_name).values()
    debug_messages.append(_debug_messages)

    if committee_code is None:
        return {"members": None, "debug": debug_messages}

    committee_code = committee_code.lower()
    debug_messages.append(f"committee_code obtained: {committee_code}")

    path = _craft_adapted_path(rel_path=path)
    debug_messages.append(f"Using committee data path: {path}")

    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    try:
        committee_id = f"{committee_code}_{congress}"
        debug_messages.append(f"Whole committee_id: {committee_id}")

    except Exception as e:

        if congress < 114:
            msg = "Only congresses between the 114th and 119th are supported"
            debug_messages.append(msg)
            raise KeyError(msg)
        
        else:
            msg = f"Couldn't find any entry for {committee_id}"
            debug_messages.append(msg)
            raise KeyError(msg)
        
    result = data.get(committee_id, [])

    # Edge case: We have got "{main_committee_code}01_{congress_num} but it is stored as {main_committee_code}_{congress_num}"
    if result == []:
        committee_id = committee_id[:-6] + committee_id[-4:]
        result = data.get(committee_id, [])
    debug_messages.append(f"Found {len(result)} members for committee_id {committee_id}")
    return {"members": result, "debug": debug_messages}


@mcp.tool(description=_get_description_for_function("get_senate_votes"))
def get_senate_votes(congress: int, session: int, roll_call_vote_no: int) -> list[dict]:

    base = "https://www.senate.gov/legislative/LIS/roll_call_votes"
    directory = f"vote{congress}{session}"
    filename = f"vote_{congress}_{session}_{roll_call_vote_no:05d}.xml"
    url = f"{base}/{directory}/{filename}"

    resp = requests.get(url)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    votes = []
    for member in root.findall(".//member"):
        votes.append({
            "name":      member.findtext("member_full") or "",
            "party":     member.findtext("party") or "",
            "member_id": member.findtext("lis_member_id") or "",
            "vote":      member.findtext("vote_cast") or "",
        })
    return votes

@mcp.tool(description=_get_description_for_function("get_house_votes"))
def get_house_votes(year: int, roll_call_number: int) -> list[dict]:

    roll = _parse_roll_call_number_house(roll_call_number)
    url = f"https://clerk.house.gov/evs/{year}/roll{roll}.xml"
    resp = requests.get(url)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    votes = []
    # iterate over each recorded-vote element
    for rv in root.findall(".//recorded-vote"):
        leg = rv.find("legislator")
        if leg is None:
            continue

        name      = (leg.text or "").strip()
        member_id = leg.attrib.get("name-id", "").strip()
        party     = leg.attrib.get("party", "").strip()
        vote_cast = (rv.findtext("vote") or "").strip()

        votes.append({
            "name":      name,
            "party":     party,
            "member_id": member_id,
            "vote":      vote_cast
        })

    return votes

@mcp.tool(description=_get_description_for_function("getCongressMember"))
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

@mcp.tool(description=_get_description_for_function("getCongressMembersByState"))
def getCongressMembersByState(stateCode: str) -> dict:
    debug = []

    stateCodes = [
        'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
        'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
        'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC'
    ]

    if stateCode not in stateCodes:
        debug.append(f"{stateCode} is not a valid U.S. State Code")
        return {"members": None, "debug": debug}

    endpoint = f"member/{stateCode}"
    root = _call_and_parse({"stateCode": stateCode}, endpoint)
    debug.append(f"Called endpoint: {endpoint}")

    members = []
    for m in root.findall(".//members/member"):
        try:
            member_data = {
                "bioguideId": m.findtext("bioguideId"),
                "name": m.findtext("name"),
                "state": m.findtext("state"),
                "party": m.findtext("partyName"),
                "district": m.findtext("district"),
                "chambers": list({term.findtext("chamber") for term in m.findall(".//terms/item/item")}),
                "url": m.findtext("url"),
                "imageUrl": m.findtext(".//depiction/imageUrl"),
            }
            members.append(member_data)
            debug.append(f"Parsed member: {member_data['name']} ({member_data['bioguideId']})")
        except Exception as e:
            debug.append(f"Failed to parse member: {e}")

    return {
        "members": members,
        "debug": debug
    }


if __name__ == "__main__":
    print("Starting Congress MCP server at PORT 8080...")
    mcp.run()

    # DEBUGGING RUNS
    # ==============
  
    # print(get_senate_votes(115, 2, 221))
    # print(get_house_votes(2018, 287))
    # print(getCongressMember("W000819"))
    # print(getBillAmendments({"congress_index" : {"congress": 116, "bill_type": "s", "bill_number": 3894}}))
    # print(getBillCommittees({"congress": 119, "bill_type": "hr", "bill_number": 1}))
    # print(extractBillActions({"congress": 115, "bill_type": "s", "bill_number": 3094}))

    # asyncio.run(_show_tools())
