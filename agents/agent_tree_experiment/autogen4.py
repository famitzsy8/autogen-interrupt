import asyncio
import yaml
import logging
from typing import Sequence, List
import openai
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage

from util.api_util import __get_api_keys
from util.other_util import _craft_adapted_path
from util.selector_util import _create_llm_selector, _create_smart_selector, _check_agent_name_safety, __augment_agent_names, __deaugment_agent_name

from PlannerAgent import PlannerAgent
from FilteredWorkbench import FilteredWorkbench
from autogen_agentchat.ui import Console



# Configure logging: selector debug to file, only warnings to console
logging.getLogger().setLevel(logging.WARNING)  # Set default level to WARNING for all loggers
selector_logger = logging.getLogger("selector")
selector_logger.setLevel(logging.INFO)

# Create file handler for selector logs
file_handler = logging.FileHandler("selector_debug.log", mode="w")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))
selector_logger.addHandler(file_handler)


async def main() -> None:
    # -------------------- Config & constants --------------------
    advancement = "advancement"
    bill = "s383-116"
    selected_agent_names = ["committee_specialist", "bill_specialist", "orchestrator", "actions_specialist", "amendment_specialist", "congress_member_specialist"]
    company_name = "ExxonMobil"

    # -------------------- Load YAML configs --------------------
    with open(_craft_adapted_path("config/agents_4.yaml"), "r") as f:
        agents_cfg = yaml.safe_load(f)
    with open(_craft_adapted_path("config/tasks_4.yaml"), "r") as f:
        tasks_cfg = yaml.safe_load(f)
    with open(_craft_adapted_path("config/prompt.yaml"), "r") as f:
        prompt_cfg = yaml.safe_load(f)

    # Concatenate NEXT_AGENT instructions to each selected agent description
    # _append_next_agent_instruction(agents_cfg, selected_agent_names)

    # -------------------- Model client --------------------
    oai_key, _ = __get_api_keys()
    model_client = OpenAIChatCompletionClient(model="gpt-4.1", api_key=oai_key)

    # -------------------- Workbench setup --------------------
    params = StdioServerParams(
        command="python",
        args=["ragMCP/main.py"],
        read_timeout_seconds=60,
    )

    async with McpWorkbench(server_params=params) as workbench:
        allowed_tool_names_orchestrator = ["getBillSummary"]
        allowed_tool_names_comm = ["get_committee_members", "get_committee_actions", "getBillCommittees"]
        allowed_tool_names_bill = ["getBillSponsors", "getBillCoSponsors", "getBillCommittees", "getRelevantBillSections", "getBillSummary"]
        allowed_tool_names_actions = ["extractBillActions", "get_committee_actions"]
        allowed_tool_names_amendments = ["getAmendmentSponsors", "getAmendmentCoSponsors", "getBillAmendments", "getAmendmentText", "getAmendmentActions"]
        allowed_tool_names_congress_members = ["getCongressMemberName", "getCongressMemberParty", "getCongressMemberState", "getBillSponsors", "getBillCoSponsors"]

        workbench_comm = FilteredWorkbench(workbench, allowed_tool_names_comm)
        workbench_bill = FilteredWorkbench(workbench, allowed_tool_names_bill)
        workbench_actions = FilteredWorkbench(workbench, allowed_tool_names_actions)
        workbench_amendments = FilteredWorkbench(workbench, allowed_tool_names_amendments)
        workbench_congress_members = FilteredWorkbench(workbench, allowed_tool_names_congress_members)
        workbench_orchestrator = FilteredWorkbench(workbench, allowed_tool_names_orchestrator)
        termination_condition = TextMentionTermination("TERMINATE")

        committee_specialist = PlannerAgent(
            name = "committee_specialist",
            description = agents_cfg["committee_specialist"]["description"].format(advancement=advancement, agent_names=selected_agent_names, company_name=company_name),
            model_client=model_client,
            workbench=workbench_comm,
            model_client_stream=True,
            reflect_on_tool_use=True
        )
        bill_specialist = PlannerAgent(
            name="bill_specialist",
            description=agents_cfg["bill_specialist"]["description"].format(agent_names=selected_agent_names, advancement=advancement, company_name=company_name),
            model_client=model_client,
            workbench=workbench_bill,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        actions_specialist = PlannerAgent(
            name="actions_specialist",
            description=agents_cfg["actions_specialist"]["description"].format(agent_names=selected_agent_names, advancement=advancement, company_name=company_name),
            model_client=model_client,
            workbench=workbench_actions,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        amendment_specialist = PlannerAgent(
            name="amendment_specialist",
            description=agents_cfg["amendment_specialist"]["description"].format(agent_names=selected_agent_names, advancement=advancement, company_name=company_name),
            model_client=model_client,
            workbench=workbench_amendments,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        congress_member_specialist = PlannerAgent(
            name="congress_member_specialist",
            description=agents_cfg["congress_member_specialist"]["description"].format(agent_names=selected_agent_names, advancement=advancement, company_name=company_name),
            model_client=model_client,
            workbench=workbench_congress_members,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        agents = [committee_specialist, bill_specialist, actions_specialist, amendment_specialist, congress_member_specialist]
        agent_names = [agent.name for agent in agents]
        orchestrator = AssistantAgent(
            name="orchestrator",
            description= agents_cfg["orchestrator"]["description"].format(bill=bill, advancement=advancement, agent_names=agent_names, company_name=company_name),
            model_client=model_client,
            model_client_stream=True,
            workbench=workbench_orchestrator
        )
        agents.append(orchestrator)
        
        # Create the selector function with access to the agent names
        smart_selector = _create_smart_selector(agent_names=[a.name for a in agents])
        llm_selector = _create_llm_selector(agent_names=[a.name for a in agents], prompt_cfg=prompt_cfg, oai_key=oai_key)


        # # Test the augment and deaugment functions
        # augmented_names = __augment_agent_names(agent_names)
        # deaugmented_names = {name: __deaugment_agent_name(name, agent_names) for name in augmented_names}
        # print(f"Augmented names: {augmented_names}")
        # print(f"Deeaugmented names: {deaugmented_names}")
        # print(f"All deaugmented names in augmented names: {all(name in deaugmented_names for name in augmented_names)}")

        if not _check_agent_name_safety(agent_names):
            raise ValueError("Agent names are not safe to use in the selector function.")

        team = SelectorGroupChat(
            agents,
            termination_condition=termination_condition,
            selector_func=llm_selector,
            model_client=model_client,
            max_turns=150
        )
        await Console(team.run_stream(task=tasks_cfg["main_task"]["description"].format(bill=bill, advancement=advancement, company_name=company_name)))

if __name__ == "__main__":
    asyncio.run(main())
