import asyncio
import yaml
import logging
import os
import threading
from queue import Queue
import sys
import select
import termios
import tty
from typing import Sequence, List
import openai
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_ext.tools.mcp import McpWorkbench, SseServerParams
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from util.config_utils import _get_key

from util.PlannerAgent import PlannerAgent
from autogen_agentchat.agents import UserProxyAgent
from helper.FilteredWorkbench import FilteredWorkbench
from autogen_agentchat.ui import Console

# -------------------- Interruption Setup --------------------
user_input_queue = Queue()

def has_key() -> bool:
    """Non-blocking check if a key has been pressed."""
    # Save the current terminal settings
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        # Set terminal to raw mode
        tty.setcbreak(sys.stdin.fileno())
        i, _, _ = select.select([sys.stdin], [], [], 0.1)  # Short timeout to avoid blocking
        return i != []
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def read_key() -> str:
    """Read a single key press without echoing."""
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        key = os.read(sys.stdin.fileno(), 1).decode()
        return key
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def user_input_thread(queue: Queue):
    """A thread that detects any key press and signals the queue."""
    while True:
        if has_key():
            # Consume the key press without echoing
            read_key()
            # Signal that input is requested
            queue.put(True)
        else:
            # Short sleep to avoid high CPU usage
            threading.Event().wait(0.1)  # 100ms poll

def _create_meta_selector(llm_selector: callable, queue: Queue) -> callable:
    """Creates a meta-selector that prioritizes user interruption signal."""
    def _meta_selector(thread: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
        if not queue.empty():
            # If there's an interruption signal, select the user_agent
            return "user_agent"
        # Otherwise, use the LLM to decide the next agent.
        return llm_selector(thread)
    return _meta_selector

# -------------------- Original Code --------------------

local_path = os.path.dirname(os.path.abspath(__file__))

def _create_llm_selector(agent_names: List[str], prompt_cfg: dict, oai_key: str) -> callable:
    """Creates a closure for the selector function that has access to agent names."""
    def _llm_selector(thread: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
        last_msg = next((m for m in reversed(thread) if isinstance(m, BaseChatMessage)), None)
        if not last_msg:
            return None

        prompt = prompt_cfg["selector_prompt"]["description"].format(agent_names=agent_names, last_message=last_msg.content)

        openai.api_key = oai_key
        response = openai.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that selects the next agent to call."},
                {"role": "user", "content": prompt}
            ]
        )
        model_result = type("ModelResult", (), {"content": response.choices[0].message.content})()

        if model_result.content.strip() in agent_names:
            return model_result.content.strip()
        else:
            return None

    return _llm_selector

async def main() -> None:
    # -------------------- Start background thread for user input --------------------
    input_thread = threading.Thread(target=user_input_thread, args=(user_input_queue,), daemon=True)
    input_thread.start()

    # -------------------- Config & constants --------------------
    bill = "s383-116"
    selected_agent_names = ["committee_specialist", "bill_specialist", "orchestrator", "actions_specialist", "amendment_specialist", "congress_member_specialist"]
    company_name = "ExxonMobil"
    year = 2018

    # -------------------- Load YAML configs --------------------
    with open(f"{local_path}/config/agents_6.yaml", "r") as f:
        agents_cfg = yaml.safe_load(f)
    with open(f"{local_path}/config/tasks_6.yaml", "r") as f:
        tasks_cfg = yaml.safe_load(f)
    with open(f"{local_path}/config/prompt_6.yaml", "r") as f:
        prompt_cfg = yaml.safe_load(f)

    # -------------------- Model client --------------------
    oai_key = _get_key("OPENAI_API_KEY")
    model_client = OpenAIChatCompletionClient(model="gpt-4.1-mini", api_key=oai_key)

    # -------------------- Workbench setup --------------------
    # Connect to ragMCP server running in separate Docker container
    ragmcp_base_url = os.getenv("RAGMCP_URL", "http://ragmcp:8080")
    ragmcp_sse_url = f"{ragmcp_base_url}/sse"  # SSE endpoint path
    params = SseServerParams(
        url=ragmcp_sse_url,
        timeout=60,  # Note: parameter name is 'timeout' not 'timeout_seconds'
    )

    async with McpWorkbench(server_params=params) as workbench:
        allowed_tool_names_orchestrator = ["getBillSummary"]
        allowed_tool_names_comm = ["get_committee_members", "get_committee_actions", "getBillCommittees"]
        allowed_tool_names_bill = ["getBillSponsors", "getBillCoSponsors", "getBillCommittees", "getRelevantBillSections", "getBillSummary"]
        allowed_tool_names_actions = ["extractBillActions", "get_committee_actions"]
        allowed_tool_names_amendments = ["getAmendmentSponsors", "getAmendmentCoSponsors", "getBillAmendments", "getAmendmentText", "getAmendmentActions"]
        allowed_tool_names_congress_members = ["getCongressMemberParty", "getCongressMemberState", "getBillSponsors", "getBillCoSponsors"]

        workbench_comm = FilteredWorkbench(workbench, allowed_tool_names_comm)
        workbench_bill = FilteredWorkbench(workbench, allowed_tool_names_bill)
        workbench_actions = FilteredWorkbench(workbench, allowed_tool_names_actions)
        workbench_amendments = FilteredWorkbench(workbench, allowed_tool_names_amendments)
        workbench_congress_members = FilteredWorkbench(workbench, allowed_tool_names_congress_members)
        workbench_orchestrator = FilteredWorkbench(workbench, allowed_tool_names_orchestrator)
        termination_condition = TextMentionTermination("TERMINATE")

        committee_specialist = PlannerAgent(
            name = "committee_specialist",
            description = agents_cfg["committee_specialist"]["description"].format(agent_names=selected_agent_names, company_name=company_name),
            model_client=model_client,
            workbench=workbench_comm,
            model_client_stream=True,
            reflect_on_tool_use=True
        )
        bill_specialist = PlannerAgent(
            name="bill_specialist",
            description=agents_cfg["bill_specialist"]["description"].format(bill=bill,agent_names=selected_agent_names, company_name=company_name),
            model_client=model_client,
            workbench=workbench_bill,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        actions_specialist = PlannerAgent(
            name="actions_specialist",
            description=agents_cfg["actions_specialist"]["description"].format(agent_names=selected_agent_names, company_name=company_name),
            model_client=model_client,
            workbench=workbench_actions,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        amendment_specialist = PlannerAgent(
            name="amendment_specialist",
            description=agents_cfg["amendment_specialist"]["description"].format(agent_names=selected_agent_names, company_name=company_name),
            model_client=model_client,
            workbench=workbench_amendments,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        congress_member_specialist = PlannerAgent(
            name="congress_member_specialist",
            description=agents_cfg["congress_member_specialist"]["description"].format(agent_names=selected_agent_names, company_name=company_name),
            model_client=model_client,
            workbench=workbench_congress_members,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        agents = [committee_specialist, bill_specialist, actions_specialist, amendment_specialist, congress_member_specialist]
        agent_names = [agent.name for agent in agents]
        orchestrator = PlannerAgent(
            name="orchestrator",
            description= agents_cfg["orchestrator"]["description"].format(bill=bill, agent_names=agent_names, company_name=company_name),
            model_client=model_client,
            model_client_stream=True,
            workbench=workbench_orchestrator
        )
        agents.append(orchestrator)

        def queue_input_func(prompt: str) -> str:
            """A custom input function that prompts for user input in the main thread."""
            # Consume the signal from the queue
            _ = user_input_queue.get()  # Remove the True signal
            # Prompt for the full message
            print("\n[Interrupt detected] " + prompt, end="")
            try:
                message = input()
                if message.lower() == 'exit':
                    raise KeyboardInterrupt("User exited via 'exit' command.")
                return message
            except EOFError:
                raise KeyboardInterrupt("Input stream closed.")

        user_agent = UserProxyAgent(
            name="user_agent",
            description=agents_cfg["user_agent"]["description"],
            input_func=queue_input_func,
        )
        # Create the selector function with access to the agent names for the LLM
        llm_agent_names = [agent.name for agent in agents]
        llm_selector = _create_llm_selector(agent_names=llm_agent_names, prompt_cfg=prompt_cfg, oai_key=oai_key)

        # Create the meta selector that wraps the LLM selector
        meta_selector = _create_meta_selector(llm_selector, user_input_queue)

        # Add the user agent to the team after the selector is created
        agents.append(user_agent)

        team = SelectorGroupChat(
            agents,
            termination_condition=termination_condition,
            selector_func=meta_selector,
            model_client=model_client,
            max_turns=150
        )
        try:
            await Console(team.run_stream(task=tasks_cfg["main_task"]["description"].format(year=year, bill_name=bill, company_name=company_name)))
        except KeyboardInterrupt:
            print("\nUser exited.")
        finally:
            # Wait for the input thread to finish if it's still alive
            if input_thread.is_alive():
                print("Waiting for input thread to close...")
                input_thread.join(timeout=1.0) # Give it a moment to join


if __name__ == "__main__":
    asyncio.run(main())