import yaml

# !/03_Code/congressMCP/.ba-venv/bin/python
# main.py

from parse_util import _call_and_parse, _parse_oai_json_response, _extract_htm_pdf_from_xml
from api_util import _get_oai_client, _get_gai_client
from other_util import _craft_adapted_path

from mcp.server.fastmcp import FastMCP

oai_client = _get_oai_client()

mcp = FastMCP(name="Congress MCP Server", host="127.0.0.1", port=8080, timeout=30)


@mcp.tool(description="Parse a LobbyView index like \"hjres44-115\" into a dict to build the Congress Index")
async def convertLVtoCongress(lobby_view_bill_id: str) -> dict:

    """
    1) Send a prompt to gpt-4o telling it to split a LobbyView database index like "hjres44-115" into
        elements like { "congress": 115, "bill_type": "hjres", "bill_number": 44 }, that can be used to build the Congress API index.
    2) Return the parsed JSON as a Python dict.
    """

    # 200 tokens
    prompt = (
        f"Take this index from the LobbyView DB (e.g. \"{lobby_view_bill_id}\")\n"
        f"and convert it into a JSON object with exactly three keys:\n"
        f"- \"congress\" (integer for the Congress number),\n"
        f"- \"bill_type\" (one of hr, s, hjres, etc.),\n"
        f"- \"bill_number\" (integer).\n\n"
        f"For example:\n"
        f"  Input: \"hjres44-115\"\n"
        f"  Output (JSON only):\n"
        f"    {{\"congress\":115, \"bill_type\":\"hjres\", \"bill_umber\":44}}\n\n"
        f"Now convert:\n"
        f"  \"{lobby_view_bill_id}\"\n\n"
        f"Respond with exactly the JSON object—no extra text."
    )

    response = await oai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )

    return _parse_oai_json_response(response)

@mcp.tool(description="Takes a Congress API index of the form { \"congress\": 115, \"bill_type\": \"hjres\", \"bill_number\": 44 } representing a bill and extracts the bill text from the Congress API")
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


@mcp.tool(description="Takes a Congress API index of the form { \"congress\": 115, \"bill_type\": \"hjres\", \"bill_number\": 44 } representing a bill and returns the cosponsors of the respective bill.")
def getBillCosponsors(congress_index: dict) -> list:
    """
    Takes:
        An obtained Congress API Index representing a bill in the format of:
        { "congress": 115, "bill_type": "hjres", "bill_number": 44 }
    
    Returns:
        A list of dictionaries containing information about each respective cosponsor of the bill. The return format will be in the form of:
        [{
            "bioguide_id": "M001189",
            "full_name": "Rep. Messer, Luke [R-IN-6]",
            "first_name": "Luke",
            "last_name": "Messer",
            "party": "R",
            "state": "IN",
            "url": "https://api.congress.gov/v3/member/M001189?format=xml",
            "district": "6",
            "sponsorship_date": "2017-02-02",
            "is_original_cosponsor": True
        }, ...]
    """
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



@mcp.tool(description="Takes a Congress API index of the form { \"congress\": 115, \"bill_type\": \"hjres\", \"bill_number\": 44 } representing a bill and returns the legislative actions that were taken on the requested bill.")
def extractBillActions(congress_index: dict) -> list:

    """
    Takes:
        An obtained Congress API Index representing a bill in the format of:
        { "congress": 115, "bill_type": "hjres", "bill_number": 44 }
    
    Returns:
        A list of dictionaries containing information about each respective legislative action taken in the U.S. Congress. The return format will be in the form of:
        [{"date": "2024-01-07", "text": ""Cloture motion on the motion...", "type": "IntroReferral" }]
    """

    root = _call_and_parse(congress_index, "bill/{congress}/{bill_type}/{bill_number}/actions")
    return [
        {
            "date": item.findtext("actionDate"),
            "text": item.findtext("text"),
            "type": item.findtext("type"),
        }
        for item in root.findall(".//actions/item")
    ]

@mcp.tool(description="Takes a Congress API index of the form { \"congress\": 115, \"bill_type\": \"hjres\", \"bill_number\": 44 } representing a bill, and returns an overview of all the amendments that have been cast on a bill")
def getAmendmentNumbers(congress_index:dict) -> dict:

    """

    Takes:
        An obtained Congress API Index representing a bill in the format of:
        { "congress": 115, "bill_type": "hjres", "bill_number": 44 }
    
    Returns:
        A list of dictionaries containing information about each amendment that has been cast on the input bill in Congress. The return format will be in the form of:
        [{
            "number": amendment number (str)
            "congress": congress session (int)
            "type": amendment type (str)
            "updateDate": last update timestamp (str, ISO 8601)
            "detailURL": API URL for the amendment detail (str)
        }]

    """

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

    return results

@mcp.tool(
    description="Takes a Congress API index of the form { \"congress\": 117, \"bill_type\": \"samdt\", \"number\": \"2137\" } representing an amendment, and returns all available text versions (PDF and HTML)."
)
def getAmendmentText(congress_index: dict) -> dict:
    """
    Takes:
        A Congress API index for an amendment in the form:
            { "congress": 117, "bill_type": "samdt", "number": "2137" }
    Returns:
        A dict containing each text version of the amendment, for example:
        {
            "pdf_url": "https://…pdf",
            "text": "The raw HTML-extracted text…"
        }
    """
    endpoint = "amendment/{congress}/{bill_type}/{number}/text"
    root = _call_and_parse(congress_index, endpoint)
    # parse_util._extract_htm_pdf_from_xml will walk <textVersions>…<formats>…
    return _extract_htm_pdf_from_xml(root, is_amendment=True)

@mcp.tool(
    description="Takes a Congress API index of the form { \"congress\": 117, \"bill_type\": \"samdt\", \"number\": \"2137\" } representing an amendment, and returns the sequence of legislative actions taken on that amendment."
)
def getAmendmentActions(congress_index: dict) -> list:
    """
    Takes:
        A Congress API index for an amendment in the form:
            { "congress": 117, "bill_type": "samdt", "number": "2137" }
    Returns:
        A list of action records, each shaped as:
        {
            "actionDate": "2021-08-08",
            "text": "Amendment SA 2137 agreed to…",
            "bill_type": "Floor",
            "actionCode": "97000",            # optional
            "sourceSystem": {                 # optional
                "code": "0",
                "name": "Senate"
            },
            "recordedVotes": [                # optional
                {
                    "rollNumber": "312",
                    "chamber": "Senate",
                    "congress": "117",
                    "date": "2021-08-09T00:45:48Z",
                    "sessionNumber": "1",
                    "url": "https://…"
                },
                ...
            ]
        }
    """
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


@mcp.tool(
    description="Takes a Congress API index of the form { \"congress\": 117, \"bill_type\": \"samdt\", \"number\": \"2137\" } representing an amendment, and returns its cosponsors along with pagination info."
)
def getAmendmentCoSponsors(congress_index: dict) -> dict:
    """
    Takes:
        A Congress API index for an amendment in the form:
            { "congress": 117, "bill_type": "samdt", "number": "2137" }
    Returns:
        A dict with:
        {
            "pagination": {
                "count": 9,
                "countIncludingWithdrawnCosponsors": 9
            },
            "cosponsors": [
                {
                    "bioguideId": "P000449",
                    "fullName": "Sen. Portman, Rob [R-OH]",
                    "firstName": "Rob",
                    "lastName": "Portman",
                    "middleName": "M.",         # optional
                    "party": "R",
                    "state": "OH",
                    "url": "https://…",
                    "sponsorshipDate": "2021-08-01",
                    "isOriginalCosponsor": True
                },
                ...
            ]
        }
    """
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

@mcp.tool(description="Takes a committee code (like hlig or hlig02) and a congress number between 113 and 119 and returns the members in the committee")
def get_committee_members(committee_code: str, congress:int,  path='data/113_119.yaml'):
    """
    Returns a list of all members (dicts) for a given committee code from the YAML file.
    Args:
        committee_code (str): The code of the committee (e.g. 'hlig')
        path (str): Path to the 113_119.yaml file
    Returns:
        list of dicts, each dict contains info about a member (name, party, rank, etc)
    """
    committee_code = committee_code.lower()
    path = _craft_adapted_path(rel_path=path)
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    try:
        committee_id = f"{committee_code}_{congress}"
    except:
        if congress < 114:
            raise KeyError("Only congresses between the 114th and 119th are supported")
        else:
            raise KeyError(f"Couldn't find any entry for{committee_id}")
    return data.get(committee_id, [])


@mcp.tool(description="Takes a formal committee or subcommittee name and returns a composed committee code")
def get_committee_code(name: str) -> str | None:
    """
    Accepts inputs of the form:
      - "House Committee on X"
      - "Senate Committee on Y"
      - "Subcommittee on Z under the House Committee on X"
      - "Subcommittee on Z under the Senate Committee on Y"
      --> Inputs must ALWAYS include the chamber
    Returns:
      - "<COMMITTEE_ID>01" for a main committee
      - "<PARENT_COMMITTEE_ID><SUB_COMMITTEE_ID>" for a subcommittee
    """
    import yaml
    import re

    path = _craft_adapted_path("data/committees_standing.yaml")
    with open(path, "r") as f:
        committees = yaml.safe_load(f)

    raw = name.strip()

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

        for c in committees:
            if c.get("name", "").strip().lower() == parent_full:
                parent_id = c.get("thomas_id")
                for sub in c.get("subcommittees", []):
                    if sub.get("name", "").strip().lower() == sub_name:
                        sub_id = sub.get("thomas_id")
                        # Compose parent + sub ids
                        return f"{parent_id}{sub_id}"
        return None

    # 2) Main committee form
    main_re = re.compile(r"^(House|Senate) Committee on (.+)$", re.IGNORECASE)
    m = main_re.match(raw)
    if m:
        chamber, main_body = m.groups()
        full = f"{chamber} Committee on {main_body}".strip().lower()

        for c in committees:
            if c.get("name", "").strip().lower() == full:
                base_id = c.get("thomas_id")
                # Append "01" for main committees
                return f"{base_id}01"
        return None

    # 3) Unrecognized format
    return None


if __name__ == "__main__":
    print("Starting Congress MCP server at PORT 8080...")
    mcp.run()