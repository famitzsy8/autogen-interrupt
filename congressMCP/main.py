# !/03_Code/congressMCP/.ba-venv/bin/python
# main.py

from parse_util import _call_and_parse, _parse_oai_json_response, _extract_htm_pdf_from_xml
from api_util import _get_oai_client

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

@mcp.tool(description="Takes a Congress API index (like { \"congress\": 115, \"bill_type\": \"hjres\", \"bill_number\": 44 }) and extracts the bill text from the Congress API")
def extractBillText(congress_index:dict) -> dict:
    """
    Takes an obtained Congress API Index in the format of:
        { "congress": 115, "bill_type": "hjres", "bill_number": 44 }
    
    And returns all the versions of the bill text, in the following format:
        {"text_version": "A short description describing the meaning of the text version", "pdf_url": "An URL that links to the PDF version of the text", "text": "The raw text"}
    """
    
    endpoint = "bill/{congress}/{bill_type}/{bill_number}/text"

    root = _call_and_parse(congress_index, endpoint)
    urls = _extract_htm_pdf_from_xml(root)

    return urls

@mcp.tool(description="Extract actions on a bill")
def extractBillActions(congress_index: dict) -> list:
    """
    congress_index: { "congress": <int>, "bill_type": <str>, "bill_number": <str> }
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


if __name__ == "__main__":
    print("Starting Congress MCP server at PORT 8080...")
    mcp.run()