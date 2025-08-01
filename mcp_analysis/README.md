# MCP Server for U.S. Congress Data Retrieval

This is an **MCP Server** that serves as the interface, a **data-retrieval agent** can use to dynamically retrieve data from the **United States Congress API**. 

## List of MCP Functions

This is the list of concrete Python functions that an agent has access to.

### `convertLVtoCongress`

Converts the LobbyView abbreviation of a bill to a dictionary that splits the important information (e.g. s3094-115 --> senate, bill 3094, 115th congress)

### `extractBillText`

Extracts the text content of a specific bill 

### `getBillCosponsors`

Gets you the Congressmen that co-sponsored a bill

### `getBillCommittees`

Gets you a list of the House/Senate Committees that were involved in the legislative processing of the bill.

### `extractBillActions`

This is one of the core functions of the MCP servers: It extracts a timeline of actions in Congress that have been taken on the bill. An example would be something like ("Bill got introduced in the House, The House proceeded with 1 hour of debate on the bill, Bill failed by roll call vote: 212-223")

### `getBillAmendments`

A function that gives you back the list of amendments that have been proposed to the bill.

### `getAmendmentText`

Gets the full text of the proposed amendment.

### `getAmendmentActions`

As with `getBillActions` it gets all the legislative actions that have been taken on an amendment to the bill (e.g. "Amendment 23 got introduced by Representative X, Amendment failed by roll call vote: 217-218")

### `getAmendmentCoSponsors`

As with `getBillCosponsors` it returns all the Congressmen that have co-sponsored this amendment

### `get_committee_members`

This function takes a formal committee name (e.g. Senate Committee on Banking, Housing and Urban Affairs) for a specific Congress and returns all the members of the Committee by rank and party

### `get_house_votes`

Given a roll call number (that one can find in `getBillActions` or `getAmendmentActions`) it returns all the House representatives and how they voted

### `get_senate_vote`

Given a record vote number (roll call number but for the Senate) it returns all the Senators and how they voted

### `getCongressMember`

Given the Congress ID of a Congress(wo)man it returns detailed information about the Congres(wo)man's name, party and congresses served

### `getCongressMembersByState`

Gets all the Congressmen (Senate and House) that come from a specific U.S. State
