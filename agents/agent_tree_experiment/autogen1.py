# The file where I ran the first version of a autogen multi-agent system, with elaborated prompts
# and dynamic MCP tooling

import asyncio

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from util.api_util import __get_api_keys
from autogen_agentchat.ui import Console
from PlannerAgent import PlannerAgent
from FilteredWorkbench import FilteredWorkbench
from util.other_util import _craft_adapted_path

import yaml

with open(_craft_adapted_path('config/agents_3.yaml'), 'r') as file:
    agents_config = yaml.safe_load(file)

with open(_craft_adapted_path('config/tasks_3.yaml'), 'r') as file:
    tasks_config = yaml.safe_load(file)

with open(_craft_adapted_path('config/prompt.yaml'), 'r') as file:
    prompt_config = yaml.safe_load(file)

oai_key, _ = __get_api_keys()
model_client = OpenAIChatCompletionClient(
    model="gpt-4.1",
    api_key=oai_key
)

async def main() -> None:
    params = StdioServerParams(
        command="python",
        args=["congressMCP/main.py"],
        read_timeout_seconds=60,
    )

    # You can also use `start()` and `stop()` to manage the session.
    async with McpWorkbench(server_params=params) as workbench:
        allowed_tool_names_comm = ["get_committee_members", "getBillCommittees", "get_committee_meeting", "get_committee_report"]
        allowed_tool_names_bill = ["extractBillText", "getBillSponsors", "getBillCoSponsors"]
        allowed_tool_names_actions = ["extractBillActions"]

        workbench_comm = FilteredWorkbench(workbench, allowed_tool_names_comm)
        workbench_bill = FilteredWorkbench(workbench, allowed_tool_names_bill)
        workbench_actions = FilteredWorkbench(workbench, allowed_tool_names_actions)
        
        termination_condition = TextMentionTermination("TERMINATE")

        agent = PlannerAgent(
            name = "committee_specialist",
            description = agents_config["committee_specialist"]["description"],
            model_client=model_client,
            workbench=workbench_comm,
            model_client_stream=True,
            reflect_on_tool_use=True
        )
        bill_specialist = PlannerAgent(
            name="bill_specialist",
            description=agents_config["bill_specialist"]["description"],
            model_client=model_client,
            workbench=workbench_bill,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        actions_agent = PlannerAgent(
            name="actions_specialist",
            description=agents_config["actions_agent"]["description"],
            model_client=model_client,
            workbench=workbench_actions,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        agents = [agent, bill_specialist, actions_agent]
        agent_names = [agent.name for agent in agents]
        advancement = "advancement"
        bill = "hr3301-116"
        orchestrator = AssistantAgent(
            name="orchestrator",
            description= agents_config["orchestrator"]["description"].format(bill=bill, advancement=advancement, agent_names=agent_names),
            model_client=model_client,
            model_client_stream=True,
        )
        agents.append(orchestrator)

        selector_prompt = prompt_config["selector_prompt"]["description"].format(agent_names=agent_names, advancement=advancement, bill=bill)

        team = SelectorGroupChat(
            agents,
            termination_condition=termination_condition,
            selector_prompt=selector_prompt,
            model_client=model_client
        )
        await Console(team.run_stream(task=tasks_config["main_task"]["description"].format(bill=bill, advancement=advancement)))


asyncio.run(main())