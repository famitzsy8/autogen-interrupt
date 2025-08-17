# 
# main.py

import yaml
import re
import requests
import xml.etree.ElementTree as ET
import ast
from typing import Any

from util.parse_util import _call_and_parse, _parse_oai_json_response, _extract_htm_pdf_from_xml, _parse_roll_call_number_house, _get_committee_code, _parse_committee_report_text_links
from util.other_util import _craft_adapted_path, _get_description_for_function
from util.fetch_util import _searchAmendmentInCR
from util.rag_util import extractBillText
from util.parse_util import _parse_congress_index_from_args
from mcp.server.fastmcp import FastMCP

from rag import BillTextRAG

from crewai.project import CrewBase, agent, crew

import os, argparse, asyncio
from crewai import Crew, Agent, Task, LLM


class MCPServerWrapper:

    mcp = FastMCP(name="2nd Congress MCP Server", host="0.0.0.0", port=8080, timeout=30)

    def __init__(self):
        pass

    @mcp.tool(description=_get_description_for_function("convertLVtoCongress"))
    def convertLVtoCongress(lobby_view_bill_id: str) -> dict:
        debug = []
        if not lobby_view_bill_id:
            debug.append("Empty argument passed to convertLVtoCongress. Provide a lobby_view_bill_id like 's3688-116'.")
            return {"result": None, "debug": debug}
        pattern = r'^(s|hr|sconres|hconres|hjres|sjres)(\d{1,5})-(1\d{2}|200)$'
        match = re.match(pattern, lobby_view_bill_id.lower())
        if not match:
            debug.append(f"Could not parse lobby_view_bill_id: {lobby_view_bill_id}")
            return {"result": None, "debug": debug}
        bill_type, number, congress = match.groups()
        debug.append(f"Parsed bill_type={bill_type}, number={number}, congress={congress}")
        return {
            "result": {
                "congress": congress,
                "bill_type": bill_type,
                "bill_number": number
            },
            "debug": debug
        }

    @mcp.tool(description=_get_description_for_function("getBillCommittees"))
    @staticmethod
    def getBillCommittees(congress_index: dict) -> dict:
        debug = []
        parsed_index = _parse_congress_index_from_args(congress_index)
        if not parsed_index:
            debug.append(f"Could not parse congress_index from input: {congress_index}")
            return {"committees": [], "debug": debug}
        root = _call_and_parse(parsed_index, "bill/{congress}/{bill_type}/{bill_number}/committees")
        committees = []
        for committee in root.findall(".//committees/item"):
            try:
                c = {
                    "system_code": committee.findtext("systemCode"),
                    "name": committee.findtext("name"),
                    "chamber": committee.findtext("chamber"),
                    "type": committee.findtext("type"),
                    "subcommittees": [],
                }
                # Add subcommittees if any
                for sub in committee.findall("./subcommittees/item"):
                    sub_obj = {
                        "system_code": sub.findtext("systemCode"),
                        "name": sub.findtext("name")
                    }
                    c["subcommittees"].append(sub_obj)
                committees.append(c)
                debug.append(f"Parsed committee: {c['name']} with {len(c['subcommittees'])} subcommittees")
            except Exception as e:
                debug.append(f"Failed to parse committee: {e}")
        return {
            "committees": committees,
            "debug": debug
        }

    @mcp.tool(description=_get_description_for_function("get_committee_actions"))
    def get_committee_actions(self, congress_index: dict) -> dict:
        debug = []
        parsed_index = _parse_congress_index_from_args(congress_index)
        if not parsed_index:
            debug.append(f"Could not parse congress_index from input: {congress_index}")
            return {"committees": [], "debug": debug}
        root = _call_and_parse(parsed_index, "bill/{congress}/{bill_type}/{bill_number}/committees")
        committees = []
        for committee in root.findall(".//committees/item"):
            try:
                c = {
                    "system_code": committee.findtext("systemCode").strip(),
                    "name": committee.findtext("name").strip(),
                    "chamber": committee.findtext("chamber").strip(),
                    "type": committee.findtext("type").strip(),
                    "actions": [],
                }
                # Add committee-level activities
                for act in committee.findall("./activities/item"):
                    c["actions"].append({
                        "name": act.findtext("name").strip(),
                        "date": act.findtext("date").strip(),
                    })
                # Add subcommittees if any
                c["subcommittees"] = []
                for sub in committee.findall("./subcommittees/item"):
                    sub_obj = {
                        "system_code": sub.findtext("systemCode").strip(),
                        "name": sub.findtext("name").strip(),
                        "actions": []
                    }
                    for act in sub.findall("./activities/item"):
                        sub_obj["actions"].append({
                            "name": act.findtext("name"),
                            "date": act.findtext("date"),
                        })
                    
                    c["subcommittees"].append(sub_obj)
                committees.append(c)
                debug.append(f"Parsed committee actions: {c['name']} with {len(c['actions'])} actions")
            except Exception as e:
                debug.append(f"Failed to parse committee actions: {e}")
        return {
            "committees": committees,
            "debug": debug
        }

    @mcp.tool(description=_get_description_for_function("extractBillActions"))
    def extractBillActions(congress_index: dict) -> dict:
        debug = []
        parsed_index = _parse_congress_index_from_args(congress_index)
        if not parsed_index:
            debug.append(f"Could not parse congress_index from input: {congress_index}")
            return {"actions": [], "debug": debug}
        
        root = _call_and_parse(parsed_index, "bill/{congress}/{bill_type}/{bill_number}/actions")
        actions = [
            {
                "date": item.findtext("actionDate"),
                "text": item.findtext("text"),
                "type": item.findtext("type"),
            }
            for item in root.findall(".//actions/item")
        ]
        debug.append(f"Extracted {len(actions)} actions for bill {parsed_index}")
        return {"actions": actions, "debug": debug}



    @mcp.tool(description=_get_description_for_function("get_committee_members"))
    def get_committee_members(committee_name: str, congress: int) -> dict:
        """
        Retrieves committee members for a specific committee and congress.
        It dynamically loads the data from a congress-specific YAML file.
        """
        debug_messages = []

        # Determine the correct data file to use based on the congress number
        committee_data_path = _craft_adapted_path(f'data/committees_{congress}.yaml')
        debug_messages.append(f"Using committee data file: {committee_data_path}")

        if not os.path.exists(committee_data_path):
            msg = f"No data file found for Congress {congress}. Looked at: {committee_data_path}"
            debug_messages.append(msg)
            # Optionally, you could fall back to the large file here if needed
            # For now, we'll raise an error.
            raise FileNotFoundError(msg)

        committee_code, _debug_messages = _get_committee_code(committee_name).values()
        debug_messages.append(_debug_messages)

        if committee_code is None:
            return {"members": None, "debug": debug_messages}

        committee_code = committee_code.lower()
        debug_messages.append(f"committee_code obtained: {committee_code}")

        with open(committee_data_path, 'r') as f:
            data = yaml.safe_load(f)

        try:
            committee_id = f"{committee_code}_{congress}"
            debug_messages.append(f"Searching for committee_id: {committee_id}")
        except Exception as e:
            # This block might be less relevant now but kept for safety
            if congress < 113 or congress > 119:
                 msg = "Only congresses between the 113th and 119th are supported"
                 debug_messages.append(msg)
                 raise KeyError(msg)
            else:
                 msg = f"An unexpected error occurred building the committee_id for {congress}: {e}"
                 debug_messages.append(msg)
                 raise KeyError(msg)

        result = data.get(committee_id, [])

        # Edge case: We have got "{main_committee_code}01_{congress_num} but it is stored as {main_committee_code}_{congress_num}"
        if result == []:
            committee_id = committee_id[:-6] + committee_id[-4:]
            result = data.get(committee_id, [])
        debug_messages.append(f"Found {len(result)} members for committee_id {committee_id}")
        return {"members": result, "debug": debug_messages}


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


    @mcp.tool(description=_get_description_for_function("get_committee_meeting"))
    def get_committee_meeting(congress_index: dict) -> dict:
        """
        congress_index: {"congress": 115, "chamber": "house"/"senate", "eventid": "117-456"}

        -->

        {"title": title, "committee": committee_name, "documents": [], "witnessDocuments": [], "witnesses": []}
        """
        parsed_index = _parse_congress_index_from_args(congress_index)
        if not parsed_index:
             raise ValueError(f"Could not parse congress_index from input: {congress_index}")

        # fetch and parse XML
        parsed_index["eventid"] = ''.join(parsed_index["eventid"].split("-"))
        root = _call_and_parse(parsed_index, "committee-meeting/{congress}/{chamber}/{eventid}")

        # title
        title = root.findtext(".//committeeMeeting/title")

        # pick first committee name
        committee_elem = root.find(".//committeeMeeting/committees/item")
        committee_name = committee_elem.findtext("name") if committee_elem is not None else None

        # meeting documents
        documents = []
        for doc in root.findall(".//committeeMeeting/meetingDocuments/item"):
            documents.append({
                "name":        doc.findtext("name"),
                "documentType": doc.findtext("documentType"),
                "format":      doc.findtext("format"),
                "url":         doc.findtext("url"),
            })

        # witness documents
        witness_documents = []
        for wdoc in root.findall(".//committeeMeeting/witnessDocuments/item"):
            witness_documents.append({
                "documentType": wdoc.findtext("documentType"),
                "format":      wdoc.findtext("format"),
                "url":         wdoc.findtext("url"),
            })

        # witnesses
        witnesses = []
        for w in root.findall(".//committeeMeeting/witnesses/item"):
            witnesses.append({
                "name":         w.findtext("name"),
                "position":     w.findtext("position"),
                "organization": w.findtext("organization"),
            })

        return {
            "title":            title,
            "committee":        committee_name,
            "documents":        documents,
            "witnessDocuments": witness_documents,
            "witnesses":        witnesses,
        }


    @mcp.tool(description=_get_description_for_function("get_committee_report"))
    def get_committee_report(congress_index: dict) -> dict:
        # Unwrap if nested
        parsed_index = _parse_congress_index_from_args(congress_index)
        if not parsed_index:
            raise ValueError(f"Could not parse congress_index from input: {congress_index}")

        congress      = parsed_index.get('congress')
        report_type   = parsed_index.get('reportType')
        report_number = parsed_index.get('reportNumber')
        if not (congress and report_type and report_number):
            raise ValueError("congress_index must contain 'congress', 'reportType', and 'reportNumber'")

        # Base report endpoint
        base_endpoint = f"committee-report/{congress}/{report_type}/{report_number}"
        root = _call_and_parse(parsed_index, base_endpoint)

        report_elem = root.find('.//committeeReport')
        if report_elem is None:
            return {}

        # Core fields
        result = {
            'citation': report_elem.findtext('citation'),
            'title': report_elem.findtext('title'),
            'congress': int(report_elem.findtext('congress')) if report_elem.findtext('congress') else None,
            'chamber': report_elem.findtext('chamber'),
            'sessionNumber': report_elem.findtext('sessionNumber'),
            'reportType': report_elem.findtext('reportType'),
            'isConferenceReport': report_elem.findtext('isConferenceReport') == 'True',
            'part': report_elem.findtext('part'),
            'updateDate': report_elem.findtext('updateDate'),
            'issueDate': report_elem.findtext('issueDate'),
        }

        # Committees
        result['committees'] = [
            {
                'systemCode': c.findtext('systemCode'),
                'name': c.findtext('name'),
                'url': c.findtext('url')
            }
            for c in report_elem.findall('.//committees/item')
        ]

        # Associated bills
        result['associatedBills'] = [
            {
                'congress': int(b.findtext('congress')) if b.findtext('congress') else None,
                'type': b.findtext('type'),
                'number': b.findtext('number'),
                'url': b.findtext('url')
            }
            for b in report_elem.findall('.//associatedBill/item')
        ]

        # ---- Fetch TEXT endpoint ----
        text_root = _call_and_parse(parsed_index, base_endpoint + "/text")
        # Flatten all <formats/item> under <text/item>
        text_items = []
        for t in text_root.findall('.//text/item'):
            text_items.extend(t.findall('./formats/item'))
        result['text_links'] = _parse_committee_report_text_links(text_items)
        result['agent'] = Agent(
            role="",
            goal="",
            backstory="",
            verbose=True,
            llm=LLM(model="gpt-4o-mini", temperature=0),
        )

        return result
    
    @mcp.tool(description=_get_description_for_function("getBillAmendments"))
    def getBillAmendments(congress_index:dict) -> dict:
        debug = []
        debug.append(f"RAW ARGUMENT: {congress_index!r}")
        if not congress_index:
            debug.append("Empty argument passed to getBillAmendments. Provide a congress_index like { 'congress': 115, 'bill_type': 'hjres', 'bill_number': 44 }.")
            return {"amendments": [], "debug": debug}
        if isinstance(congress_index, dict) and 'congress_index' in congress_index:
            congress_index = congress_index['congress_index']
            debug.append("UNWRAPPED congress_index")
        debug.append(f"USING ARGUMENT: {congress_index!r}")
        endpoint = "bill/{congress}/{bill_type}/{bill_number}/amendments"
        results = []
        offset = 0
        limit = 250
        while True:
            params = {"limit": limit, "offset": offset}
            root = _call_and_parse(congress_index, endpoint, params=params)
            amendments = root.findall('.//amendment')
            if not amendments:
                break
            for am in amendments:
                results.append({
                    'number': am.findtext('number').strip(),
                    'congress': int(am.findtext('congress')),
                    'type': am.findtext('type'),
                    'updateDate': am.findtext('updateDate'),
                    'detailUrl': am.findtext('url'),
                })
            total = int(root.findtext('.//pagination/count', default='0'))
            if offset + limit >= total:
                break
            offset += limit
        debug.append(f"Found {len(results)} amendments for bill {congress_index}")
        return {
            "amendments": results,
            "debug": debug
        }

    @mcp.tool(description=_get_description_for_function("getAmendmentSponsors"))
    def getAmendmentSponsors(congress_index: dict) -> dict:
        debug = []
        debug.append(f"RAW ARGUMENT: {congress_index!r}")
        if not congress_index:
            debug.append("Empty argument passed to getAmendmentSponsors. Provide a congress_index with 'congress', 'amendment_type', and 'amdt_number'.")
            return {'sponsors': [], 'debug': debug}
        # unwrap if nested
        if isinstance(congress_index, dict) and 'congress_index' in congress_index:
            congress_index = congress_index['congress_index']
            debug.append("UNWRAPPED congress_index")
        debug.append(f"USING ARGUMENT: {congress_index!r}")
        # extract parameters
        congress = congress_index.get('congress')
        amendment_type = congress_index.get('amendment_type')
        amendment_number = congress_index.get('amdt_number')
        if not (congress and amendment_type and amendment_number):
            debug.append("congress_index must include 'congress', 'amendment_type', and 'amdt_number'")
            return {'sponsors': [], 'debug': debug}
        # build endpoint
        endpoint = f"amendment/{congress}/{amendment_type}/{amendment_number}"
        params = {"format": "xml"}
        # call API and parse XML
        root = _call_and_parse(congress_index, endpoint, params=params)
        sponsors = []
        for item in root.findall('.//sponsors/item'):
            sponsors.append({
                'bioguideId': item.findtext('bioguideId').strip() if item.findtext('bioguideId') else None,
                'firstName': item.findtext('firstName').strip() if item.findtext('firstName') else None,
                'lastName': item.findtext('lastName').strip() if item.findtext('lastName') else None,
                'fullName': item.findtext('fullName').strip() if item.findtext('fullName') else None,
                'party': item.findtext('party').strip() if item.findtext('party') else None,
                'state': item.findtext('state').strip() if item.findtext('state') else None,
                'url': item.findtext('url').strip() if item.findtext('url') else None,
            })
        debug.append(f"Found {len(sponsors)} amendment sponsors for {congress_index}")
        return {
            'sponsors': sponsors,
            'debug': debug
        }

    @mcp.tool(description=_get_description_for_function("getAmendmentText"))
    def getAmendmentText(congress_index: dict) -> dict:
        debug = []
        if not congress_index:
            debug.append("Empty argument passed to getAmendmentText. Provide a congress_index with 'congress', 'amendment_type', and 'amdt_number'.")
            return {"text_urls": {}, "debug": debug}
        endpoint = "amendment/{congress}/{amendment_type}/{amdt_number}/text"
        root = _call_and_parse(congress_index, endpoint)
        text_urls = _extract_htm_pdf_from_xml(root, is_amendment=True)
        if text_urls == {}:
            text_from_cr = _searchAmendmentInCR(amendment=congress_index)
            text_urls["pdf_url"] = ""
            text_urls["text"] = text_from_cr
        debug.append(f"Extracted amendment text for {congress_index}")
        return {"text_urls": text_urls, "debug": debug}
        

    @mcp.tool(description=_get_description_for_function("getAmendmentActions"))
    def getAmendmentActions(congress_index: dict) -> dict:
        debug = []
        if not congress_index:
            debug.append("Empty argument passed to getAmendmentActions. Provide a congress_index with 'congress', 'amendment_type', and 'number'.")
            return {"actions": [], "debug": debug}
        endpoint = "amendment/{congress}/{amendment_type}/{number}/actions"
        root = _call_and_parse(congress_index, endpoint)
        actions = []
        for item in root.findall(".//actions/item"):
            action = {
                "actionDate": item.findtext("actionDate"),
                "text":       item.findtext("text"),
                "type":       item.findtext("type"),
            }
            if item.findtext("actionCode") is not None:
                action["actionCode"] = item.findtext("actionCode")
            ss = item.find("sourceSystem")
            if ss is not None:
                action["sourceSystem"] = {
                    "code": ss.findtext("code"),
                    "name": ss.findtext("name"),
                }
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
        debug.append(f"Extracted {len(actions)} amendment actions for {congress_index}")
        return {"actions": actions, "debug": debug}

    @mcp.tool(description=_get_description_for_function("getAmendmentCoSponsors"))
    def getAmendmentCoSponsors(congress_index: dict) -> dict:
        debug = []
        if not congress_index:
            debug.append("Empty argument passed to getAmendmentCoSponsors. Provide a congress_index with 'congress', 'amendment_type', and 'number'.")
            return {"pagination": {}, "cosponsors": [], "debug": debug}
        endpoint = "amendment/{congress}/{amendment_type}/{number}/cosponsors"
        root = _call_and_parse(congress_index, endpoint)
        pag = root.find(".//pagination")
        pagination = {
            "count": int(pag.findtext("count", default="0")),
            "countIncludingWithdrawnCosponsors": int(
                pag.findtext("countIncludingWithdrawnCosponsors", default="0")
            ),
        }
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
                "isOriginalCosponsor": item.findtext("isOriginalCosponsor") == "True",
            }
            if item.findtext("middleName") is not None:
                cs["middleName"] = item.findtext("middleName")
            cosponsors.append(cs)
        debug.append(f"Found {len(cosponsors)} amendment cosponsors for {congress_index}")
        return {
            "pagination": pagination,
            "cosponsors": cosponsors,
            "debug": debug
        }

    @mcp.tool(description=_get_description_for_function("getRelevantBillSections"))
    def getRelevantBillSections(self, congress_index: dict, company_name: str) -> dict:
        bill_text = extractBillText(congress_index)
        raw_text = bill_text["text_versions"]["text"]

        bill_text_file_name = f"{congress_index['bill_type']}{congress_index['bill_number']}-{congress_index['congress']}.txt"
        print(f"Bill text file name: {bill_text_file_name}")
        # Save raw text to file
        with open(f"congressMCP/texts/{bill_text_file_name}", "w") as f:
            f.write(raw_text)
        
        bill_text_rag = BillTextRAG(bill_text_file_name)
        return bill_text_rag.run(company_name=company_name, bill_name=f"{congress_index['congress']}{congress_index['bill_type']}-{congress_index['bill_number']}")

    def run(self):
        print("Starting 2nd Congress MCP server at PORT 8080...")
        self.mcp.run()

    def _debugging_runs(self):
        # print(self.getCommitteeReport({"congress": 116, "reportType": "srpt", "reportNumber": "288"}))
        # print("\n\n" + 50 * "#" + "\n\n")
        # print(self.getBillCommittees({"congress": 119, "bill_type": "hr", "bill_number": 1}))
        print("\n\n" + 50 * "#" + "\n\n")
        # print(self.get_committee_meeting({"congress": 118, "chamber": "house", "eventid": "115-538"}))
        #print(self.getRelevantBillSections({"congress": 114, "bill_type": "s", "bill_number": 2012}, "Exxon Mobil"))
        print(self.get_committee_actions({"congress": 115, "bill_type": "hr", "bill_number": 2917}))


if __name__ == "__main__":
    # print("Starting 2nd Congress MCP server at PORT 8080...")
    # mcp.run()

    # # DEBUGGING RUNS
    # # ==============

    # print(getBillCommittees({"congress": 119, "bill_type": "hr", "bill_number": 1}))

    # print(get_committee_meeting({"congress": 118, "chamber": "house", "eventid": "115-538"}))
    # print("n\n" + 50 * "#" + "\n\n")
    server = MCPServerWrapper()

    # s2012-114
    server._debugging_runs()
    # print(server.getRelevantBillSections({"congress": 114, "bill_type": "s", "bill_number": 2012}, "Exxon Mobil"))
    # server = MCPServerWrapper()
    # server.run()