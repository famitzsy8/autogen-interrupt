from autogen_core.models import _model_client
from pydantic import config
import yaml
from typing import Sequence, List

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING
import openai

from pathlib import Path
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams, SseServerParams
from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent, UserProxyAgent
from autogen_agentchat.agents._user_control_agent import UserControlAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_core import Agent, CancellationToken
from autogen_core.tools import FunctionTool
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.teams import BaseGroupChat
from autogen_agentchat.teams._group_chat._selector_group_chat import SelectorGroupChat
from openai import AsyncOpenAI

from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage


# from _hierarchical_groupchat import HierarchicalGroupChat # TODO: handle the allowedTransitions field for the general factory of Group Chats

from handlers.agent_input_queue import AgentInputQueue
from agents.PlannerAgent import PlannerAgent
from tools.FilteredWorkbench import FilteredWorkbench

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



async def enhance_selector_prompt(
    user_selector_prompt: str, model_client: AsyncOpenAI
) -> str:
    """
    Enhance user-provided selector prompt using LLM.

    Takes a user input selector prompt and enhances it with structured information about:
    - Participant names and roles
    - When to call User_proxy for feedback
    - Message history context

    Args:
        user_selector_prompt: Raw selector prompt from user
        model_client: OpenAI model client for LLM call

    Returns:
        Enhanced selector prompt with proper structure
    """
    logger.info("Starting selector prompt enhancement")
    logger.debug(f"Original user selector prompt:\n{user_selector_prompt}")

    enhancement_prompt = f"""You are helping optimize an agent selector prompt for a multi-agent system.

The user has provided this selector prompt: "{user_selector_prompt}"

Your task is to enhance this prompt to be clear and structured. The enhanced prompt MUST include:

1. A clear reference to {{participants}} - the list of available agents
2. A clear reference to {{roles}} - what each agent does
3. Clear guidance on when to call the User_proxy agent (when user feedback or approval is needed)
4. A reference to {{history}} - the conversation history for context

The enhanced prompt should:
- Be concise but complete
- Use the template variables: {{participants}}, {{roles}}, {{history}}, User_proxy
- Maintain the user's intent while adding structure
- Make it clear that User_proxy should only be called when user feedback/approval is truly needed

Provide ONLY the enhanced selector prompt, no additional text."""

    response = await model_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": enhancement_prompt}],
    )

    enhanced_prompt = response.content if hasattr(response, "content") else str(response)

    logger.info("Selector prompt enhancement completed")
    logger.info(f"Enhanced selector prompt:\n{enhanced_prompt}")
    logger.debug(f"Original prompt:\n{user_selector_prompt}")

    return enhanced_prompt


def load_data():
    # Use relative path - team.yaml is in the same factory directory
    config_path = Path(__file__).parent / "team.yaml"

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        f.close()
        return data

config_data = load_data()

@dataclass
class AgentTeamContext:

    team: BaseGroupChat
    user_control: UserControlAgent
    participant_names: list[str]
    display_names: dict[str, str]  # Maps agent_name -> display_name

async def init_team(
    api_key: str,
    agent_input_queue: AgentInputQueue,
    max_messages: int = 60,
    selector_prompt: str | None = None,
    company_name: str | None = None,
    bill_name: str | None = None,
    congress: str | None = None
) -> AgentTeamContext:

    model_client = OpenAIChatCompletionClient(
        model=config_data["llm"]["model_client_args"]["model"],
        api_key=api_key
    )

    agents = []
    enhance_prompt_client = AsyncOpenAI(api_key=api_key)
    has_user_proxy = config_data["team"]["group_chat_args"]["has_user_proxy"]

    if has_user_proxy and agent_input_queue is not None:
        user_proxy_agent_name = config_data["team"]["group_chat_args"]["user_proxy_name"]
        async def user_proxy_input(
            prompt: str, cancellation_token: CancellationToken | None = None
        ) -> str:

            return await agent_input_queue.get_input(
                prompt=prompt,
                cancellation_token=cancellation_token,
                agent_name=user_proxy_agent_name
            )

        # Format user_proxy description with config values if available
        user_proxy_description = config_data["agents"][user_proxy_agent_name]["description"]
        if company_name and bill_name and congress:
            all_agent_names = list(config_data["agents"].keys())
            agent_names_str = ", ".join(all_agent_names)
            user_proxy_description = user_proxy_description.format(
                company_name=company_name,
                bill_name=bill_name,
                bill=bill_name,
                year=congress,
                congress=congress,
                agent_names=agent_names_str
            )

        user_proxy = UserProxyAgent(
            name=user_proxy_agent_name,
            description=user_proxy_description,
            input_func=user_proxy_input, # This listens to the WebSocket input configured in agent_input_queue
        )

    if config_data["team"]["mcp_url"] is not None:
        params = globals()[config_data["team"]["params_class"]](
            url = config_data["team"]["mcp_url"],
            timeout = config_data["team"].get("mcp_timeout", 60)
        )
        async with McpWorkbench(server_params = params) as workbench:
            agents = await build_agents(
                workbench,
                model_client=model_client,
                company_name=company_name,
                bill_name=bill_name,
                congress=congress
            )
    else:
        agents = await build_agents(
            None,
            model_client=model_client,
            company_name=company_name,
            bill_name=bill_name,
            congress=congress
        )
    

    if selector_prompt is not None:
        enhanced_selector_prompt = await enhance_selector_prompt(
            user_selector_prompt=selector_prompt,
            model_client=enhance_prompt_client
        )
        selector_prompt = enhanced_selector_prompt
    else:
        selector_prompt = build_default_selector_prompt(
            agent_names=[a.name for a in agents],
            api_key=api_key
        )

    team = globals()[config_data["team"]["group_chat_class"]](
        participants=agents,
        termination_condition=MaxMessageTermination(max_messages=max_messages),
        selector_func=selector_prompt,
        model_client=model_client,
        agent_input_queue=agent_input_queue
    )

    user_control = UserControlAgent(name="You")

    # Build display_names mapping from agent_name to display_name
    display_names = {}
    for agent_config in config_data["agents"].values():
        agent_name = agent_config["name"]
        display_name = agent_config.get("display_name", agent_name)
        display_names[agent_name] = display_name

    # Add special display names
    display_names["You"] = "You"
    display_names["User"] = "User"
    display_names["System"] = "System"

    return AgentTeamContext(
        team=team,
        user_control=user_control,
        participant_names=[a.name for a in agents],
        display_names=display_names
    )


async def build_agents(
    workbench: McpWorkbench | None,
    model_client: OpenAIChatCompletionClient,
    company_name: str | None = None,
    bill_name: str | None = None,
    congress: str | None = None
):

    agents = []

    for agent_name, agent_cfg in config_data["agents"].items():
        # Format agent description with config values if available
        description = agent_cfg["description"]
        if company_name and bill_name and congress:
            # Get all agent names for {agent_names} placeholder
            all_agent_names = list(config_data["agents"].keys())
            agent_names_str = ", ".join(all_agent_names)

            description = description.format(
                company_name=company_name,
                bill_name=bill_name,
                bill=bill_name,  # {bill} is same as {bill_name}
                year=congress,    # {year} maps to congress
                congress=congress,
                agent_names=agent_names_str
            )

        if workbench is None:
            a = globals()[agent_cfg["agent_class"]](
                name = agent_cfg["name"],
                model_client = model_client,
                system_message = agent_cfg["system_message"], # TODO: check if including a '' system message affects behavior of the agents
                description = description,
                model_client_stream = agent_cfg.get("model_client_stream", False),
                reflect_on_tool_use = agent_cfg.get("reflect_on_tool_use", False)
            )
            agents.append(a)
        else:
            a = globals()[agent_cfg["agent_class"]](
                name = agent_cfg["name"],
                model_client = model_client,
                system_message = agent_cfg["system_message"], # TODO: check if including a '' system message affects behavior of the agents
                description = description,
                model_client_stream = agent_cfg.get("model_client_stream", False),
                workbench = globals()[agent_cfg["tools"]["workbench_class"]](
                    workbench,
                    agent_cfg["tools"]["allowed_tool_names"]
                ),
                reflect_on_tool_use = agent_cfg.get("reflect_on_tool_use", False)
            )
            agents.append(a)

    return agents
    
def build_default_selector_prompt(agent_names: List[str], api_key: str) -> callable:

    # This function returns a default selector prompt that is called by the GCM and gives it access to the last message
    def _default_selector(thread: Sequence[BaseAgentEvent | BaseChatMessage]) -> str| None:
        last_msg = next((m for m in reversed(thread) if isinstance(m, BaseChatMessage)), None)
        if not last_msg:
            return None
        prompt = config_data["team"]["group_chat_args"]["default_selector_prompt"].format(
            agent_names=agent_names,
            last_message=last_msg.content
        )

        openai.api_key = api_key
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
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
    return _default_selector

