"""
AutoGen version of the multi-agent lobbying workflow defined for CrewAI.

Agents (same roles as YAML):
  A  coordinator_agent        – orchestrates everything
  B  actions_overview_agent   – timeline “hot-spot” analyst
  C  committee_agent          – committee specialist
  D  amendment_agent          – amendment specialist
  E  bill_text_agent          – bill-text specialist
  F  data_fetch_agent         – raw-data retriever via MCP tools

Execution order / dependencies
  1) A → F   (fetch all raw data)
  2) A → C,D (committee / amendment analysis, needs data from F)
  3) A → E   (bill-text analysis, needs data from F)
  4) A → B   (timeline hot-spots, needs C & D outputs + data)
  5) A synthesises everything into the final report
"""

import asyncio
import os
import yaml
from pathlib import Path

from autogen import AssistantAgent, LLMConfig
from autogen.mcp import create_toolkit
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Fail-safe import of local module api_util
import sys, os
sys.path.append(os.getcwd())
from agents.util.api_util import __get_api_keys


def load_config(file_path: str) -> dict:
    """Loads a YAML configuration file."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)


def create_agent(name: str, config: dict, llm_config: LLMConfig) -> AssistantAgent:
    """Creates an AssistantAgent from a config dictionary."""
    system_message = (
        f"You are a helpful AI assistant. Your name is {name}.\n"
        f"Your role is: {config['role']}\n"
        f"Your goal is: {config['goal']}\n"
        f"Your backstory is: {config['backstory']}\n"
        "You must follow all instructions and do not need to ask for clarification."
    )
    return AssistantAgent(
        name=name,
        system_message=system_message,
        llm_config=llm_config
    )


async def main():
    """
    Main asynchronous function to run the AutoGen multi-agent workflow.
    """
    # --- Configuration ---
    bill = "s3688-116"
    company = "ExxonMobil"

    agents_config = load_config("./agents/tests/config/agents.yaml")

    api_key, _ = __get_api_keys()
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    # Use a single LLMConfig for all agents
    llm_config = LLMConfig(
        config_list=[{"model": "gpt-4.1-mini", "api_key": api_key}],
        cache_seed=42  # Use caching for reproducibility
    )

    # --- MCP Server Setup ---
    server_params = StdioServerParameters(
        command="python",
        args=["congressMCP/main.py"],
    )

    print("--- Starting Multi-Agent Workflow with AutoGen and MCP ---")
    async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        print("MCP Session Initialized.")

        # # Create a toolkit from the running MCP server
        # toolkit = await create_toolkit(session=session)
        # print(f"Toolkit created with {len(toolkit.tools)} tools.")

        # --- Agent Creation ---
        print("🤖 Creating agents...")
        coordinator_agent = create_agent('Coordinator', agents_config['coordinator_agent'], llm_config)
        actions_overview_agent = create_agent('Actions_Overview', agents_config['actions_overview_agent'], llm_config)
        committee_agent = create_agent('Committee_Analyst', agents_config['committee_agent'], llm_config)
        amendment_agent = create_agent('Amendment_Analyst', agents_config['amendment_agent'], llm_config)
        bill_text_agent = create_agent('Bill_Text_Analyst', agents_config['bill_text_agent'], llm_config)
        data_fetch_agent = create_agent('Data_Fetcher', agents_config['data_fetch_agent'], llm_config)

        # Register the MCP toolkit ONLY for the data_fetch_agent
        # toolkit.register_for_llm(data_fetch_agent)
        # print("Registered MCP tools with Data_Fetcher agent.")

        # --- Workflow Execution ---
        print("\n--- Starting Task Execution ---")

        # Step 1: Fetch all data using the specialist agent (F)
        print("\n[Step 1/4]  F: Data_Fetcher is gathering all data...")
        fetch_prompt = (
            f"Create all primary data for bill {bill}. "
            "This includes the full action timeline, committee details, amendment list, and bill texts. "
            "Return the raw data as a JSON object."
            "**After responding, DO NOT SUGGEST any more tools, DO NOT call any tools again, and TERMINATE the conversation.**"
        )
        f_response = await data_fetch_agent.a_run(
            message=fetch_prompt,
            # tools=toolkit.tools,
            max_turns=20,
            user_input=False
        )
        await f_response.process()
        fetched_data = f_response.final_answer
        print("F: Data fetching complete.")

        # Step 2: Run specialist analyses (C, D, E) in parallel
        print("\n[Step 2/4] C, D, E: Specialist agents are analyzing data in parallel...")
        committee_prompt = (
            f"Analyze the committee data provided below for bill {bill} in the context of {company}.\n"
            f"DATA:\n```json\n{fetched_data}\n```\n"
            "Provide an overall relevance score (1-5), a member alignment table, and a narrative of the committee's impact."
        )
        amendment_prompt = (
            f"Analyze the amendment data provided below for bill {bill} for its impact on {company}.\n"
            f"DATA:\n```json\n{fetched_data}\n```\n"
            "Highlight relevant passages and score each amendment's relevance (1-5)."
        )
        bill_text_prompt = (
            f"Analyze the full bill text provided below for its significance to {company}.\n"
            f"DATA:\n```json\n{fetched_data}\n```\n"
            "Quote up to seven of the most significant passages, providing location, relevance score, and a brief impact note."
        )

        c_task = committee_agent.a_run(message=committee_prompt)
        d_task = amendment_agent.a_run(message=amendment_prompt)
        e_task = bill_text_agent.a_run(message=bill_text_prompt)

        c_response, d_response, e_response = await asyncio.gather(c_task, d_task, e_task)
        await asyncio.gather(c_response.process(), d_response.process(), e_response.process())

        committee_analysis = c_response.final_answer
        amendment_analysis = d_response.final_answer
        bill_text_analysis = e_response.final_answer
        print("C, D, E: Specialist analyses complete.")

        # Step 3: Synthesize timeline and actions (B)
        print("\n[Step 3/4] B: Actions_Overview agent is synthesizing analyses...")
        actions_prompt = (
            f"You are the Congressional Timeline Analyst. Synthesize a report on the key legislative events for bill {bill}.\n"
            "Integrate the following analyses to identify high-leverage moments (introductions, referrals, votes).\n"
            f"\n--- COMMITTEE ANALYSIS ---\n{committee_analysis}\n"
            f"\n--- AMENDMENT ANALYSIS ---\n{amendment_analysis}\n"
            f"\n--- RAW DATA ---\n{fetched_data}\n"
            "Your final output should be a narrative summarizing the bill's journey and flagging critical lobbying opportunities for {company}."
        )
        b_response = await actions_overview_agent.a_run(message=actions_prompt)
        await b_response.process()
        actions_analysis = b_response.final_answer
        print("B: Actions overview complete.")

        # Step 4: Final coordination and strategic output (A)
        print("\n[Step 4/4] A: Coordinator is creating the final lobbying strategy...")
        coordinator_prompt = (
            "You are the Lobbying Strategy Orchestrator. Your task is to create the final, board-ready lobbying heat-map and strategic guidance for {company} regarding bill {bill}.\n"
            "You must synthesize the two comprehensive reports provided below. Do not fetch any new data. Your output is the definitive strategy.\n"
            f"\n--- LEGISLATIVE JOURNEY & ACTIONS OVERVIEW ---\n{actions_analysis}\n"
            f"\n--- BILL TEXT ANALYSIS ---\n{bill_text_analysis}\n"
            "Produce a clear, actionable report that pinpoints where lobbying money and effort should be directed."
        )
        a_response = await coordinator_agent.a_run(message=coordinator_prompt)
        await a_response.process()
        final_report = a_response.final_answer
        print("A: Final report complete.")

        # --- Final Output ---
        print("\n\n---FINAL REPORT ---")
        print(final_report)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ValueError as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("\nWorkflow interrupted by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}") 