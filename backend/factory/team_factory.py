# Standard library imports
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List, Sequence

# Third-party imports
import openai
import yaml
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.agents._user_control_agent import UserControlAgent
from autogen_agentchat.conditions import TextMentionTermination, ExternalTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.teams import BaseGroupChat
from autogen_agentchat.teams._group_chat._selector_group_chat import SelectorGroupChat
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams, SseServerParams
from openai import AsyncOpenAI

# Plugin imports
from autogen_agentchat.teams._group_chat.plugins.state_context import StateContextPlugin
from autogen_agentchat.teams._group_chat.plugins.analysis_watchlist import (
    AnalysisWatchlistPlugin,
    AnalysisService,
    AnalysisComponent,
)

# Local imports
from agents.PlannerAgent import PlannerAgent
from handlers.agent_input_queue import AgentInputQueue
from tools.FilteredWorkbench import FilteredWorkbench
from teams.hierarchical_groupchat import HierarchicalGroupChat, HierarchicalGroupChatManager

from factory.registry import FunctionRegistry
from factory.function_loader import FunctionLoader
from factory.input_function_registry import InputFunctionRegistry
from factory.input_function_loader import InputFunctionLoader


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
    external_termination: ExternalTermination  # For user-initiated termination
    state_context_plugin: StateContextPlugin | None = None  # For state queries via websocket

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

    registry = FunctionRegistry()
    registry.load_from_module("factory.tool_functions")

    if registry.get_errors():
        for error in registry.get_errors():
            logger.warning(f"   {error}")
    
    loader = FunctionLoader(registry)

    # Initialize input function registry
    input_func_registry = InputFunctionRegistry()
    input_func_registry.load_from_module("factory.input_functions")

    if input_func_registry.get_errors():
        for error in input_func_registry.get_errors():
            logger.warning(f"   {error}")

    input_func_loader = InputFunctionLoader(input_func_registry)

    if has_user_proxy and agent_input_queue is not None:
        user_proxy_agent_name = config_data["team"]["group_chat_args"]["user_proxy_name"]
        user_proxy_config = config_data["agents"][user_proxy_agent_name]
        input_func_name = user_proxy_config.get("input_func", "queue_based_input")

        # Retrieve input function template and wrap in closure
        input_func_template = input_func_loader.get_input_function(input_func_name)

        async def user_proxy_input(
            prompt: str, cancellation_token: CancellationToken | None = None
        ) -> str:
            return await input_func_template(
                agent_input_queue=agent_input_queue,
                agent_name=user_proxy_agent_name,
                prompt=prompt,
                cancellation_token=cancellation_token,
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
        # UserProxyAgent will be added to agents list after build_agents

    if config_data["team"]["mcp_url"] is not None:
        params = globals()[config_data["team"]["params_class"]](
            url = config_data["team"]["mcp_url"],
            timeout = config_data["team"].get("mcp_timeout", 60)
        )
        async with McpWorkbench(server_params = params) as workbench:
            agents = await build_agents(
                workbench,
                model_client=model_client,
                loader=loader,
                company_name=company_name,
                bill_name=bill_name,
                congress=congress
            )
    else:
        agents = await build_agents(
            None,
            model_client=model_client,
            company_name=company_name,
            loader=loader,
            bill_name=bill_name,
            congress=congress
        )

    # Add UserProxyAgent to agents list if it was created
    if has_user_proxy and agent_input_queue is not None:
        agents.insert(0, user_proxy)  # Insert at beginning for selector to prefer other agents first

    # Extract state context configuration from team config
    enable_state_context = config_data["team"].get("enable_state_context", True)
    user_proxy_name = config_data["team"]["group_chat_args"].get("user_proxy_name", "user_proxy")
    initial_handoff_context = config_data["team"].get("initial_handoff_context")
    initial_state_of_run = config_data["team"].get("initial_state_of_run")

    # Create plugins list
    plugins: list = []
    state_context_plugin: StateContextPlugin | None = None

    # Create StateContextPlugin if enabled
    if enable_state_context:
        state_context_plugin = StateContextPlugin(
            model_client=model_client,
            user_proxy_name=user_proxy_name,
            initial_state_of_run=initial_state_of_run or "",
            initial_handoff_context=initial_handoff_context or "",
        )
        plugins.append(state_context_plugin)

    # Determine group chat class and build appropriate selector
    group_chat_class_name = config_data["team"]["group_chat_class"]

    # Create external termination for user-initiated termination
    external_termination = ExternalTermination()

    # For HierarchicalGroupChat, use selector_prompt as a string
    # For SelectorGroupChat (congress), use selector_func as a callable
    if group_chat_class_name == "HierarchicalGroupChat":
        # Use selector_prompt as a string template
        if selector_prompt is not None:
            selector_prompt_str = await enhance_selector_prompt(
                user_selector_prompt=selector_prompt,
                model_client=enhance_prompt_client
            )
        else:
            selector_prompt_str = config_data["team"]["group_chat_args"]["default_selector_prompt"]

        # Combine text mention termination with external termination
        text_termination = TextMentionTermination("<TERMINATE>", [a.name for a in agents if a.name not in ["user", "You", user_proxy_name]])
        combined_termination = text_termination | external_termination

        team_kwargs = {
            "participants": agents,
            "termination_condition": combined_termination,
            "selector_prompt": selector_prompt_str,
            "model_client": model_client,
            "agent_input_queue": agent_input_queue,
            "emit_team_events": True,  # Enable state update events
            "plugins": plugins,  # Pass plugins list instead of individual state parameters
        }

        allowed_transitions = config_data["team"]["group_chat_args"].get("allowed_transitions")
        if allowed_transitions is None:
            raise ValueError("allowed_transitions must be specified in group_chat_args for HierarchicalGroupChat")

        team = globals()[group_chat_class_name](
            allowed_transitions=allowed_transitions,
            **team_kwargs
        )
    else:
        # For SelectorGroupChat with state context enabled:
        # The selector prompt string is injected with fresh state variables by _select_speaker()
        # Do NOT use build_default_selector_prompt() as it's incompatible with state context
        selector_prompt_str = config_data["team"]["group_chat_args"]["default_selector_prompt"]

        # Combine text mention termination with external termination
        text_termination = TextMentionTermination("<TERMINATE>", [a.name for a in agents if a.name not in ["You", "user", user_proxy_name]])
        combined_termination = text_termination | external_termination

        team_kwargs = {
            "participants": agents,
            "termination_condition": combined_termination,
            "selector_prompt": selector_prompt_str,
            "model_client": model_client,
            "agent_input_queue": agent_input_queue,
            "emit_team_events": True,  # Enable state update events
            "plugins": plugins,  # Pass plugins list instead of individual state parameters
        }

        team = globals()[group_chat_class_name](**team_kwargs)

        # Set team reference on the group chat so selector can access it
        # The selector needs this to set _feedback_context on the team instance
        team._team_reference = team

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
        display_names=display_names,
        external_termination=external_termination,
        state_context_plugin=state_context_plugin
    )


async def build_agents(
    workbench: McpWorkbench | None,
    model_client: OpenAIChatCompletionClient,
    loader: FunctionLoader,
    company_name: str | None = None,
    bill_name: str | None = None,
    congress: str | None = None
):

    agents = []

    for _, agent_cfg in config_data["agents"].items():
        # Skip UserProxyAgent - it's created separately in init_team with special handling
        if agent_cfg["agent_class"] == "UserProxyAgent":
            continue
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
            python_tools = []
            if "python_tools" in agent_cfg.get("tools", {}):
                tool_names = agent_cfg["tools"]["python_tools"] # TODO: make sure python_tools is in YAML
                python_tools = loader.get_tool_functions_by_names(tool_names)
            
            agent_kwargs = {
                "name": agent_cfg["name"],
                "model_client": model_client,
                "system_message": agent_cfg["system_message"],
                "description": description,
                "model_client_stream": agent_cfg.get("model_client_stream", False),
                "reflect_on_tool_use": agent_cfg.get("reflect_on_tool_use", False),
                "include_state_in_context": agent_cfg.get("include_state_in_context", False)
            }

            if python_tools:
                agent_kwargs["tools"] = python_tools

            a = globals()[agent_cfg["agent_class"]](**agent_kwargs)
            agents.append(a)

        else:
            python_tools = []
            if "python_tools" in agent_cfg.get("tools", {}):
                tool_names = agent_cfg["tools"]["python_tools"]
                python_tools = loader.get_tool_functions_by_names(tool_names)
            
            mcp_workbench = None
            if "mcp_tools" in agent_cfg.get("tools", {}):
                mcp_workbench = globals()[agent_cfg["tools"]["mcp_tools"]["workbench_class"]](
                    workbench,
                    agent_cfg["tools"]["mcp_tools"]["allowed_tool_names"]
                )

            agent_kwargs = {
                "name": agent_cfg["name"],
                "model_client": model_client,
                "system_message": agent_cfg["system_message"],
                "description": description,
                "model_client_stream": agent_cfg.get("model_client_stream", False),
                "reflect_on_tool_use": agent_cfg.get("reflect_on_tool_use", False),
                "include_state_in_context": agent_cfg.get("include_state_in_context", False)
            }

            # Cannot use both workbench and tools - workbench takes precedence
            if mcp_workbench:
                agent_kwargs["workbench"] = mcp_workbench
            elif python_tools:
                agent_kwargs["tools"] = python_tools
            
            a = globals()[agent_cfg["agent_class"]](**agent_kwargs)
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

