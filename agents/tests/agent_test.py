from crewai import Agent, Task, Crew
from crewai import LLM
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters
import os
from agents.prototypes.api_util import __get_api_keys

oai_key, gai_key = __get_api_keys()

gemini_flash = LLM(model="gemini/gemini-2.0-flash",
    temperature=0.7,api_key=gai_key)

gpt4o_mini = LLM("openai/gpt-4o-mini", temperature=0.7, api_key=oai_key)

server_params=StdioServerParameters(
    command="python", 
    args=["congressMCP/main.py"]
)

# Example usage (uncomment and adapt once server_params is set):
with MCPServerAdapter(server_params) as mcp_tools:
    print(f"Available tools: {[tool.name for tool in mcp_tools]}")
    
    mcp_agent = Agent(
        role="MCP Tool User and Usage Coordinator",
        goal="Give precise answers to the tasks based on the data that you can fetch with the MCP Tools",
        backstory="You are a specialist in United States Congress politics, and you are given the MCP (Model Context Protocol) tools to navigate through the Congress API. You know that each bill has its legislative actions, where committee referrals, roll call vote numbers (House) and record vote numbers (Senate) can be found, which are of course a number distinct from the bill number. You also know that you don't need to fetch the bill text in order to get the cosponsors or the roll call/record vote numbers, there are seperate functions for this.",
        tools=mcp_tools, # Pass the loaded tools to your agent
        reasoning=True,
        verbose=True,
        llm = gemini_flash
    )

    filter_agent = Agent(
        role="Filter voting records by a specific criterion",
        goal="Giving back only the voting records that come from politicians with the specific criterion fulfilled (e.g. they are from a certain state)",
        backstory="You are a specialist in United States Congress politics, and you are given the task to filter out a list of voting records by a certain criterion. An example for this criterion would be that the politicians need to be Democrats. Another exaample would be that they need to belong to a ceratin committee.",
        tools=mcp_tools, # Pass the loaded tools to your agent
        reasoning=True,
        verbose=True,
        llm = gemini_flash
    )
    # tasks = [
    #     Task(
    #         description="Fetch the number of amendments for bill {bill}.",
    #         agent=agent,
    #         expected_output="A JSON list of actions."
    #     )
    # ]

    task1 = Task(
            description="Get the voting outcomes of all record votes in the Senate for bill {bill}",
            agent=mcp_agent,
            expected_output="Output all the voting records for Senate record votes in bill {bill} in PURE JSON FORMAT, such that it can be re-used by another task."
        )
    task2 = Task(
            description="Given the voting outcomes fetched, filter out all votes that are not from Michigan. In other words, give back only the voting records from Michigan representatives and/or senators.",
            agent=filter_agent,
            expected_output="A list of all voting records of Michigan politicians in {bill}",
            context=[task1]
        )

    # function_testing_tasks = {
    #     "convertLVtoCongress": Task(
    #         description="Convert the LobbyView bill ID {bill} to a structured Congress API index.",
    #         agent=agent,
    #         expected_output="A dictionary with keys: congress, bill_type, bill_number."
    #     ),
    #     "extractBillText": Task(
    #         description="Extract all available versions of the bill text for {bill} (as a Congress API index).",
    #         agent=agent,
    #         expected_output="A dictionary with text versions, each containing a description, PDF URL, and raw text."
    #     ),
    #     "getBillCosponsors": Task(
    #         description="Fetch all cosponsors for the bill {bill} (as a Congress API index).",
    #         agent=agent,
    #         expected_output="A list of dictionaries, each with cosponsor info (bioguide_id, name, party, state, etc.)."
    #     ),
    #     "extractBillActions": Task(
    #         description="Fetch all legislative actions for the bill {bill} (as a Congress API index).",
    #         agent=agent,
    #         expected_output="A list of dictionaries, each with date, text, and type of action."
    #     ),
    #     "getAmendmentNumbers": Task(
    #         description="Fetch all amendments for the bill {bill} (as a Congress API index).",
    #         agent=agent,
    #         expected_output="A list of dictionaries, each with amendment number, congress, type, updateDate, and detailUrl."
    #     ),
    #     "getAmendmentText": Task(
    #         description="Fetch all available text versions for the amendment {amendment} (as a Congress API index).",
    #         agent=agent,
    #         expected_output="A dictionary with text versions, each containing a PDF URL and raw text."
    #     ),
    #     "getAmendmentActions": Task(
    #         description="Fetch all legislative actions for the amendment {amendment} (as a Congress API index).",
    #         agent=agent,
    #         expected_output="A list of action records for the amendment, each with date, text, type, and optional vote info."
    #     ),
    #     "getAmendmentCoSponsors": Task(
    #         description="Fetch all cosponsors for the amendment {amendment} (as a Congress API index).",
    #         agent=agent,
    #         expected_output="A dictionary with pagination info and a list of cosponsor dictionaries."
    #     ),
    #     "get_committee_members": Task(
    #         description="Fetch all members of the committee with code {committee_code} for congress {congress}.",
    #         agent=agent,
    #         expected_output="A list of dictionaries, each with info about a committee member."
    #     ),
    #     "get_committee_code": Task(
    #         description="Convert the formal committee or subcommittee name {committee_name} to a committee code.",
    #         agent=agent,
    #         expected_output="A string committee code or None if not found."
    #     ),
    #     "get_senate_votes": Task(
    #         description="Fetch all votes for the given Senate roll call: congress {congress}, session {session}, roll_call_vote_no {roll_call_vote_no}.",
    #         agent=agent,
    #         expected_output="A list of dictionaries, each with name, party, member_id, and vote."
    #     ),
    #     "get_house_votes": Task(
    #         description="Fetch all votes for the given House roll call: year {year}, roll {roll}.",
    #         agent=agent,
    #         expected_output="A list of dictionaries, each with name, party, member_id, and vote."
    #     ),
    #     "getCongressMember": Task(
    #         description="Fetch info for the Congress member with bioguideId {bioguideId}.",
    #         agent=agent,
    #         expected_output="A dictionary with fullName, state, party, congressesServed, and debug info."
    #     ),
    #     "getCongressMembersByState": Task(
    #         description="Fetch all Congress members for the state with code {stateCode}.",
    #         agent=agent,
    #         expected_output="A dictionary with a list of members and debug info."
    #     ),
    # }
    # tasks = [
    #     Task(
    #         description="Fetch all actions for bill {bill}. Output JSON.",
    #         agent=agent,
    #         expected_output="A JSON list of actions."
    #     ),
    #     Task(
    #         description="Fetch all amendments for bill {bill}. Output JSON.",
    #         agent=agent,
    #         expected_output="A JSON list of amendments."
    #     ),
    #     Task(
    #         description="Fetch all roll call votes for bill {bill}. Output JSON.",
    #         agent=agent,
    #         expected_output="A JSON list of roll call votes."
    #     ),
    #     Task(
    #         description="Summarize the key steps in the bill's process, referencing the fetched actions, amendments, and roll calls.",
    #         agent=agent,
    #         expected_output="A markdown summary."
    #     )
    # ]

    # task1 = Task(
    #     description="""
    #     1. extract all the legislative actions from bill {bill}\n
    #     2. extract the text of the bill
    #     3. check if there exist any amendments, and if there do exist any extract their text.
    #     4. Consider that ExxonMobil lobbied for this bill with {amount} dollars. 
    #         Go through all actions and amendments, and the texts obtained from the bill 
    #         (and possibly from the amendments) and highlight the key actions and text extracts, 
    #         where we can see ExxonMobil's lobbying efforts showing, or their interests represented
    #     5. Output a list of all the concrete legislative actions, and 10 concrete text extracts which are highly relevant for the interests of ExxonMobil
    #     """,
    #     agent=agent,
    #     expected_output="An overview over all the legislative actions, on the bill and on the amendments, where ExxonMobil's interests are most evidently represented or being disputed"
    # )

    # task1 = Task(
    #     description="Fetch all the committee members involved in the legislative actions for bill {bill}. For this, first fetch the right committee code, and then use it to fetch the committee members.",
    #     agent=agent,
    #     expected_output="A list of all committee members of the involved committees"
    # )

    # task2 = Task(
    #     description="""
    #     Now you are a political science researcher, a specialist in lobbying in the United States Congress. 
    #     Given all of these legislative information that you obtained from the previous task, do the following:
    #     1. Assess which of these processes and text extracts would be the most worth putting lobbying efforts in for ExxonMobil and which less
    #     2. Rank the information based on involvement relevance for ExxonMobil
    #     3. Output it nicely in markdown format for copy-pasting
    #     """,
    #     agent=agent,
    #     expected_output="A ranking of all the legislative actions and texts based on relevance for ExxonMobil's lobbying involvement."
    # )

    crew = Crew(
        agents=[mcp_agent, filter_agent],
        tasks=[task1, task2],
        verbose=True
    )

    result = crew.kickoff(
        inputs={
            "bill":"hr1625-115",
            "amount":"1000000"
    })

    print(result)