# !/03_Code/.ba-venv/bin/python
# prototype_multiagent1.py

import os, argparse, asyncio
from crewai import Crew, Agent, Task, LLM
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters
from agents.prototypes.api_util import __get_api_keys

# Here we parse the command line arguments
# s3094-115 is a light-weight bill, for a heavier bill "hr1625-115" can be used
parser = argparse.ArgumentParser()
parser.add_argument("--bill",    required=True, help="e.g. s3094-115")
parser.add_argument("--company", required=True, help="e.g. ExxonMobil")
args = parser.parse_args()

oai_key, gai_key = __get_api_keys()

# Temperatures were chosen 0 over all models, such that they only work with the data they obtained
# from the MCP server. This is however sub-optimal, and a clearer model usage structure needs to be elaborated
# with varying atrributes like temperature
gemini_flash_notemp = LLM("gemini/gemini-2.5-pro", temperature=0.0, api_key=gai_key)
gemini_flash = LLM("gemini/gemini-2.5-pro", temperature=0.0, api_key=gai_key)

gpt4o = LLM("openai/gpt-4o", temperature=0.0, api_key=oai_key)
gpt4o_mini   = LLM("openai/gpt-4o-mini",     temperature=0.0, api_key=oai_key)
gpt4_1_mini = LLM("openai/gpt-4.1-mini", temperature=0.0, api_key=oai_key)
o4_mini = LLM("openai/o4-mini", temperature=0.0, api_key=oai_key) # o4-mini doesn't work because it doesn't accept the "stop" keyword

# Here we build the interface between CrewAI agents and the MCP server
stdio_params = StdioServerParameters(
    command="python", args=["congressMCP/main.py"]
)
mcp_adapter = MCPServerAdapter(stdio_params)


BILL_SLOT     = "{bill}"
COMPANY_SLOT  = "{company}"

# A set of overarching rules that tries to mitigate hallucination - probably not that useful though --> TEST WITHOUT
COMMON_RULES = """
    You MUST:
    • rely exclusively on the JSON you receive or on MCP tool calls — do NOT invent data
    • output JSON if asked, otherwise markdown is fine
    • keep citations (roll-call numbers, amendment numbers, committee codes) verbatim
"""

# A description of the different agents can be found in the local README.md
with mcp_adapter as mcp_tools:

    actions_agent = Agent(
        role        = "Actions Agent",
        goal        = "Fetch the legislative actions of {bill} via MCP tools.",
        backstory   = (
            "You speak the Congress API fluently through MCP. "
            "Never summarise and never invent anything — just return the raw JSON response from the tools you call to fetch the actions."
        ),
        tools       = mcp_tools,
        reasoning   = True,
        verbose     = True,
        llm         = gemini_flash_notemp
    )

    interests_scanner_agent = Agent(
        role      = "Lobby-Interest Scanner",
        goal      = (
            "Identify which stages of the bill {bill} offer the greatest leverage "
            "for {company}'s lobbying influence and delegate deeper research to other agents."
        ),
        backstory = (
            "You are a senior lobby strategist who fetches the legislative actions from the MCP servers and analyzes them in-depth: committee referral, "
            "select amendments, or pivotal floor votes. You scrutinize these actions, determining which actions are important in the lobbying process for {company}'s interests, "
            "but you NEVER invent or hallucinate actions that never happened, all the actions base your reasoning on are directly fetched from the MCP server."
            "IMPORTANT: If the MCP call returns just one action, you simply work with this one action, you never invent any other actions OK?????"
        ),
        tools     = mcp_tools,
        reasoning = True,
        verbose   = True,
        llm       = gpt4o
    )

    bill_text_agent = Agent(
        role      = "Bill Text Analyst",
        goal      = (
            "Analyze the full text of {bill} and identify sections, provisions, or language that are most relevant to {company}'s interests. "
            "Highlight up to 5 key passages that could significantly benefit or harm {company}, and explain why."
        ),
        backstory = (
            "You are a legislative analyst with expertise in bill text interpretation. "
            "You fetch the full bill text using MCP tools and carefully read through it, flagging any sections that are likely to impact {company}'s business, regulatory, or public affairs interests. "
            "You do not summarize the entire bill, but focus on the most relevant and impactful sections."
        ),
        tools     = mcp_tools,
        reasoning = True,
        verbose   = True,
        llm       = gpt4_1_mini
    )

    committee_agent = Agent(
        role      = "Committee Influence Analyst",
        goal      = (
            "Determine how committee membership and committee actions affect {company}'s interests"
            "in the bill."
        ),
        backstory = (
            "Former senior Congressional staffer. Maps committee stage to "
            "member ideology and corporate ties, and determines the usefulness of the actions "
            "in the committee itself for {company}."
        ),
        tools     = mcp_tools,
        reasoning = True,
        verbose   = True,
        llm       = gpt4_1_mini
    )

    amendment_agent = Agent(
        role      = "Amendment Text Examiner",
        goal      = (
            "Pinpoint amendments (and sponsors) that materially benefit {company}, by looking at the text and the actions."
        ),
        backstory = (
            "You comb amendment texts for giveaways, loopholes, subsidies, or "
            "regulatory rollbacks that align with the company."
        ),
        tools     = mcp_tools,
        reasoning = True,
        verbose   = True,
        llm       = gpt4_1_mini
    )

    parent_agent = Agent(
        role      = "Lobby-Detection Summarizer",
        goal      = (
            "Deliver a in-depth lobbying-heat map for {company} that aggregates everything that has been found"
            "around bill {bill}."
        ),
        backstory = (
            "You supervise a specialist team. You do no direct data calls; you rely "
            "on downstream agents and reconcile their findings into one in-depth report without summarizing."
        ),
        tools     = mcp_tools,
        reasoning = True,
        verbose   = True,
        llm       = gpt4_1_mini
    )

    # ============TASKS===============
    # You can find a description of the tasks in the README.md

    fetch_actions_task = Task(
        description = (
            "Using the MCP server, fetch the COMPLETE list of legislative actions for {bill} "
            "as JSON. Return it verbatim with no commentary."
        ),
        agent           = actions_agent,
        expected_output = "JSON list of actions, each with date, text, type"
    )

    scan_hotspots_task = Task(
        description = (
            "As the interests scanner, read the action timeline for {bill} and, "
            "as a lobbyist for {company}, identify:\n"
            "• Which committees, amendments, and record/roll votes are worth deeper analysis.\n"
            "Produce three JSON arrays:\n"
            "  committees_to_inspect, amendments_to_inspect, votes_to_inspect\n"
            + COMMON_RULES
        ),
        context         = [fetch_actions_task],
        agent           = interests_scanner_agent,
        expected_output = (
            "JSON object with keys committees_to_inspect, amendments_to_inspect, "
            "votes_to_inspect"
        )
    )

    bill_text_task = Task(
        description = (
            "Fetch the full text of {bill} using the MCP server. Read through the text and highlight up to 5 passages (sections, paragraphs, or lines) that are most likely to impact {company}'s interests—either positively or negatively. "
            "For each passage, provide a short explanation of its relevance. Only include passages that are clearly significant for {company}." 
            + COMMON_RULES
        ),
        context         = [scan_hotspots_task],
        agent           = bill_text_agent,
        expected_output = (
            "Markdown list: passage → explanation of impact on {company}"
        )
    )

    committee_task = Task(
        description = (
            "Given committees_to_inspect..."
            "1. pull the committee rosters and analyse the influence on {company}'s interests. Flag members likely indifferent, moderately (supportive/opposed), (supportive/opposed) or strongly (supportive/opposed). \n"
            "2. look at the actions of the committee and determine how important the committee's actions were in order to advance {company}'s interests"
            + COMMON_RULES
        ),
        context         = [scan_hotspots_task, fetch_actions_task],
        agent           = committee_agent,
        expected_output = "Markdown table ranking members by alignment score, and another markdown table containing the committee actions with their importance" \
        "in {company}'s interest advancement in the bigger picture of all the legislative actions."
    )

    amendment_task = Task(
        description = (
            "Retrieve full texts for amendments_to_inspect. Read through all of the sections, and highlight at most 5"
            "passages that most strongly influence a {company} (potentially benefitting or damaging) and name the sponsors of the amendments that correspond to the passages.\n"
            "Also bear in mind that some amendments may not contain any sections that could benefit {company}, so only return a section if it is CLEAR that"
            "it will have an impact on {company}"
            + COMMON_RULES
        ),
        context         = [scan_hotspots_task],
        agent           = amendment_agent,
        expected_output = (
            "Markdown list: amendment_id → key passage → sponsor(s) → benefit summary"
        )
    )

    final_report_task = Task(
        description = (
            "Integrate committee and amendment analyses plus any noteworthy votes "
            "into a single lobbying-heat map for leadership at {company}." \
            "Do NOT condense what has been found by the previous tasks/agents, glue everything" \
            "together in one in-depth lengthy report."
        ),
        context         = [committee_task, amendment_task, fetch_actions_task, scan_hotspots_task],
        agent           = parent_agent,
        expected_output = "Executive summary in Markdown format ready to be copy-pasted. Does not summarize the findings" \
        "but brings them together all at once in a lengthy nicely structured report."
    )

    lobby_crew = Crew(
        agents = [
            actions_agent, interests_scanner_agent,
            committee_agent, amendment_agent, parent_agent,
            bill_text_agent
        ],
        tasks  = [
            fetch_actions_task, scan_hotspots_task,
            committee_task, amendment_task, final_report_task,
            bill_text_task
        ],
        tools=mcp_tools,
        verbose = True
    )

    result = lobby_crew.kickoff(
        inputs = { "bill": args.bill, "company": args.company }
    )

    print("\n" + "#" * 80 + "\nFINAL REPORT\n" + "#" * 80)
    print(result)