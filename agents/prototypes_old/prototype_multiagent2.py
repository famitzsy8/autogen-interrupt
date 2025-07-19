# !/03_Code/.ba-venv/bin/python
# prototype_multiagent2.py
"""
prototype_multiagent_v2.py  —  CrewAI "V2" prototype

This crew expands the original V1 proof‑of‑concept into a fully‑featured, end‑to‑end
legislative‑intelligence workflow.  All major phases of a bill’s life‑cycle are
handled by specialised agents that collaborate through the MCP tool‑chain.

Key improvements
----------------
* **Richer data ingestion** – dedicated tasks for sponsors / co‑sponsors, committee
  reports, vote records, amendment metadata & text.
* **Relevance scoring** – every analytical agent returns a 1‑5 relevance score so
  the orchestrator can build a weighted lobbying heat‑map.
* **Deterministic tool use** – low‑temperature models for data retrieval, slightly
  warmer models for synthesis, all wrapped with a shared `COMMON_RULES` block to
  minimise hallucination.
* **Clear dependency graph** – downstream tasks consume the _JSON_ produced by
  upstream tasks; no task talks directly to the web or invents data.
* **Single final artefact** – the `HeatMap Orchestrator` stitches together all
  findings into a board‑ready, sectioned Markdown report (no summarisation, just
  aggregation & formatting).

Run:
-----
    python prototype_multiagent_v2.py --bill s3094-115 --company "ExxonMobil"
"""

import argparse, os
from crewai import Crew, Agent, Task, LLM
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters
from agents.prototypes.api_util import __get_api_keys

#───────────────────────────
# CLI arguments
#───────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--bill",    required=True, help="e.g. s3094-115")
parser.add_argument("--company", required=True, help="e.g. ExxonMobil")
args = parser.parse_args()

BILL_SLOT    = "{bill}"
COMPANY_SLOT = "{company}"

oai_key, gai_key = __get_api_keys(path="../../secrets.ini")

#───────────────────────────
# LLM registry (tweak temps as needed)
#───────────────────────────
llms = {
    "retrieval":      LLM("gemini/gemini-2.5-pro", temperature=0.0, api_key=gai_key),
    "analysis":       LLM("openai/gpt-4o",        temperature=0.1, api_key=oai_key),
    "synthesis":      LLM("openai/gpt-4.1-mini",  temperature=0.15, api_key=oai_key),
}

#───────────────────────────
# MCP bridge
#───────────────────────────
stdio_params = StdioServerParameters(command="python", args=["congressMCP/main.py"])
with MCPServerAdapter(stdio_params) as mcp_tools:

    # Shared anti‑hallucination rules
    COMMON_RULES = (
        "You MUST:\n"
        "• rely exclusively on the JSON you receive or on MCP tool calls — do NOT invent data\n"
        "• output JSON if asked, otherwise markdown is fine\n"
        "• keep citations (roll‑call numbers, amendment numbers, committee codes) verbatim\n"
    )

    #───────────────────────
    # Agents
    #───────────────────────

    sponsor_agent = Agent(
        role = "Sponsorship Retriever",
        goal = "Fetch sponsors & co‑sponsors for {bill} and return raw JSON.",
        backstory = "Reads Congress data through MCP; does not summarise.",
        tools = mcp_tools,
        reasoning = True,
        verbose = True,
        llm = llms["retrieval"],
    )

    actions_agent = Agent(
        role = "Timeline Retriever",
        goal = "Fetch complete legislative action timeline for {bill} (JSON).",
        backstory = "Fluent in Congress API via MCP; never invents actions.",
        tools = mcp_tools,
        reasoning = True,
        verbose = True,
        llm = llms["retrieval"],
    )

    committee_meta_agent = Agent(
        role = "Committee Meta Collector",
        goal = "Gather committees, members, actions & reports for {bill}.",
        backstory = "Former committee clerk; expert at committee artefacts.",
        tools = mcp_tools,
        reasoning = True,
        verbose = True,
        llm = llms["retrieval"],
    )

    amendment_meta_agent = Agent(
        role = "Amendment Meta Collector",
        goal = "Gather amendments, sponsors, co‑sponsors & actions for {bill}.",
        backstory = "Tracks amendment lifecycle & metadata via MCP.",
        tools = mcp_tools,
        reasoning = True,
        verbose = True,
        llm = llms["retrieval"],
    )

    bill_text_agent = Agent(
        role = "Bill Text Analyst",
        goal = "Identify up to 7 passages in the bill text highly relevant to {company} and score relevance 1‑5.",
        backstory = "Legislative counsel specialising in industry impact analysis.",
        tools = mcp_tools,
        reasoning = True,
        verbose = True,
        llm = llms["analysis"],
    )

    committee_analysis_agent = Agent(
        role = "Committee Influence Analyst",
        goal = "Score committee events & member roles (1‑5 relevance to {company}).",
        backstory = "Ex‑staff director mapping ideology & corporate ties.",
        tools = mcp_tools,
        reasoning = True,
        verbose = True,
        llm = llms["analysis"],
    )

    amendment_analysis_agent = Agent(
        role = "Amendment Relevance Analyst",
        goal = "Score amendment texts 1‑5 for relevance to {company}; highlight passages.",
        backstory = "Amendment hopper guru spotting giveaways & poison pills.",
        tools = mcp_tools,
        reasoning = True,
        verbose = True,
        llm = llms["analysis"],
    )

    vote_analysis_agent = Agent(
        role = "Vote Pattern Analyst",
        goal = "Fetch House & Senate votes for {bill}; tag each 1‑5 relevance to {company}.",
        backstory = "Parliamentary procedure wonk focusing on vote dynamics.",
        tools = mcp_tools,
        reasoning = True,
        verbose = True,
        llm = llms["analysis"],
    )

    orchestrator_agent = Agent(
        role = "HeatMap Orchestrator",
        goal = "Produce an exhaustive lobbying heat‑map & phase budget guidance for {company}.",
        backstory = (
            "You supervise a multi‑agent research crew.  You **never** fetch data yourself; "
            "instead you integrate all downstream JSON & markdown outputs into a single, "
            "structured deliverable for C‑suite lobby leadership.  Absolutely no summarising — "
            "include full findings verbatim under clear headings."
        ),
        tools = mcp_tools,
        reasoning = True,
        verbose = True,
        llm = llms["synthesis"],
    )

    #───────────────────────
    # Tasks (data‑gathering tier)
    #───────────────────────

    fetch_sponsors_task = Task(
        description = (
            "Using MCP, fetch primary sponsors and co‑sponsors for {bill}. "
            "Return the raw JSON exactly as provided by the tool — no commentary."
        ),
        agent = sponsor_agent,
        expected_output = "JSON with sponsors & cosponsors"
    )

    fetch_actions_task = Task(
        description = (
            "Using MCP, fetch the **complete** action timeline for {bill}.  Return verbatim JSON."
        ),
        agent = actions_agent,
        expected_output = "JSON list of actions"
    )

    fetch_committee_meta_task = Task(
        description = (
            "Gather committee metadata for {bill}: list committees; for each, pull actions, reports, and full roster.  "
            "Return a JSON structure grouping these artefacts under each committee code.  " + COMMON_RULES
        ),
        agent = committee_meta_agent,
        context = [fetch_actions_task],
        expected_output = "Nested JSON {committee_code: {actions:[], reports:[], members:[]}}"
    )

    fetch_amendment_meta_task = Task(
        description = (
            "Gather **all** amendments for {bill}.  For each amendment pull actions, sponsors, co‑sponsors, and full text. "
            "Return a JSON array of amendment objects." + COMMON_RULES
        ),
        agent = amendment_meta_agent,
        context = [fetch_actions_task],
        expected_output = "JSON list of amendments with metadata"
    )

    fetch_votes_task = Task(
        description = (
            "Using MCP, pull House and Senate vote records for {bill} (incl. roll numbers).  Return raw JSON." + COMMON_RULES
        ),
        agent = vote_analysis_agent,  # same agent will later analyse
        expected_output = "JSON with vote arrays (house_votes, senate_votes)"
    )

    #───────────────────────
    # Tasks (analysis tier)
    #───────────────────────

    analyse_bill_text_task = Task(
        description = (
            "Fetch bill text for {bill}.  Select up to 7 passages most relevant to {company}. "
            "For each passage provide: location (section/page/line), quoted text, 1‑5 relevance score, and a short impact note." + COMMON_RULES
        ),
        agent = bill_text_agent,
        context = [fetch_sponsors_task],
        expected_output = "Markdown table of passages with relevance scores"
    )

    analyse_committee_task = Task(
        description = (
            "For each committee gathered, assess:\n"
            "• Overall committee relevance score (1‑5) to {company}.\n"
            "• Per‑member alignment flags (Indifferent / ±Moderate / ±Strong).\n"
            "• Narrative of how committee actions & reports shape the bill vis‑à‑vis {company}." + COMMON_RULES
        ),
        agent = committee_analysis_agent,
        context = [fetch_committee_meta_task],
        expected_output = "Markdown with committee relevance scores & member table"
    )

    analyse_amendments_task = Task(
        description = (
            "For each amendment, read the text and rate relevance to {company} (1‑5).  Highlight up to 3 key clauses per highly relevant amendment. "
            "Return Markdown bullet list grouped by relevance tier." + COMMON_RULES
        ),
        agent = amendment_analysis_agent,
        context = [fetch_amendment_meta_task],
        expected_output = "Markdown with amendment analysis & scores"
    )

    analyse_votes_task = Task(
        description = (
            "Analyse the vote JSON: identify any votes with material impact on bill trajectory.  For each, provide the roll number, what was voted on, outcome, "
            "and relevance score (1‑5) for {company}." + COMMON_RULES
        ),
        agent = vote_analysis_agent,
        context = [fetch_votes_task, analyse_committee_task],  # may use committee alignment to interpret votes
        expected_output = "Markdown table of relevant votes & scores"
    )

    #───────────────────────
    # Final synthesis
    #───────────────────────

    heatmap_task = Task(
        description = (
            "Integrate **all** previous findings into a single, richly formatted lobbying heat‑map. "
            "Sections:** Sponsors & Co‑Sponsors • Timeline Hot‑spots • Committee Stage • Amendments • Votes • Bill Text Passages • Budget Allocation Guidance.\n"
            "For each legislative phase output a 🔥/🟡/🟦 heat label determined by weighted average of relevance scores.\n"
            "Do **not** summarise or aggregate into high‑level bullet points; instead embed each agent's full markdown/JSON under collapsible headings so nothing is lost."),
        agent = orchestrator_agent,
        context = [
            fetch_sponsors_task,
            fetch_actions_task,
            analyse_bill_text_task,
            analyse_committee_task,
            analyse_amendments_task,
            analyse_votes_task
        ],
        expected_output = "Complete board‑ready Markdown report with heat‑map & full annexes"
    )

    #───────────────────────
    # Crew assembly & run
    #───────────────────────

    crew = Crew(
        agents=[
            sponsor_agent, actions_agent, committee_meta_agent, amendment_meta_agent,
            bill_text_agent, committee_analysis_agent, amendment_analysis_agent,
            vote_analysis_agent, orchestrator_agent
        ],
        tasks=[
            fetch_sponsors_task, fetch_actions_task, fetch_committee_meta_task,
            fetch_amendment_meta_task, fetch_votes_task,
            analyse_bill_text_task, analyse_committee_task, analyse_amendments_task,
            analyse_votes_task, heatmap_task
        ],
        tools=mcp_tools,
        verbose=True,
    )

    result = crew.kickoff(inputs={"bill": args.bill, "company": args.company})

    print("\n" + "#" * 80 + "\nFINAL REPORT\n" + "#" * 80)
    print(result)
