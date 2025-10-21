"""Research team setup logic adapted from dr_interrupt.py."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent, UserProxyAgent
from autogen_agentchat.agents._user_control_agent import UserControlAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_core import CancellationToken
from autogen_core.tools import FunctionTool
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import OpenAIChatCompletionClient
from openai import AsyncOpenAI

from _hierarchical_groupchat import HierarchicalGroupChat

if TYPE_CHECKING:
    from agent_input_queue import AgentInputQueue

INITIAL_TOPIC = """
I want to know which professors are most key in the selection process for the Cogmaster in Paris.
""".strip()


@dataclass
class ResearchContext:
    """Holds reusable objects for the research team and control."""

    team: HierarchicalGroupChat
    user_control: UserControlAgent
    participant_names: list[str]


def build_research_team(
    api_key: str,
    max_messages: int = 60,
    agent_input_queue: AgentInputQueue | None = None,
) -> ResearchContext:
    """
    Create the research agents, hierarchical group chat, and control helpers.

    Preserves exact agent configurations from dr_interrupt.py CLI (system messages, tools, etc).

    Args:
        api_key: OpenAI API key for model client
        max_messages: Maximum number of messages before termination (default: 60)
        agent_input_queue: Optional input queue for User_proxy requiring human input

    Returns:
        ResearchContext containing team, user control, and participant names
    """
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=api_key,
    )

    web_search_client = AsyncOpenAI(api_key=api_key)

    # Human-in-the-loop admin using UserProxyAgent with WebSocket input
    user_proxy = None
    if agent_input_queue is not None:
        # Create a wrapper that includes agent name in the input request
        async def user_proxy_input(
            prompt: str, cancellation_token: CancellationToken | None = None
        ) -> str:
            return await agent_input_queue.get_input(
                prompt=prompt,
                cancellation_token=cancellation_token,
                agent_name="User_proxy",
            )

        user_proxy = UserProxyAgent(
            name="User_proxy",
            description=(
                "A human admin who can approve plans and provide guidance. "
                "Call this agent for approvals, troubleshooting, or secrets/API keys."
            ),
            input_func=user_proxy_input,  # WebSocket input instead of stdin
        )

    developer = AssistantAgent(
        name="Developer",
        model_client=model_client,
        system_message="""You are an AI developer. You follow an approved plan, follow these guidelines:
        1. You write python/shell code to solve tasks.
        2. Wrap the code in a code block that specifies the script type.
        3. The user can't modify your code. So do not suggest incomplete code which requires others to modify.
        4. You should print the specific code you would like the executor to run.
        5. Don't include multiple code blocks in one response.
        6. If you need to import libraries, use ```bash pip install module_name```, please send a code block that installs these libraries and then send the script with the full implementation code
        7. Check the execution result returned by the executor,  If the result indicates there is an error, fix the error and output the code again
        8. Do not show appreciation in your responses, say only what is necessary.
        9. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
        """,
        description="""Call this Agent if:
            You need to write code.
            DO NOT CALL THIS AGENT IF:
            You need to execute the code.""",
        model_client_stream=True,
    )

    planner = AssistantAgent(
        name="Planner",
        system_message="""You are an AI Planner,  follow these guidelines:
        1. Your plan should include 5 steps, you should provide a detailed plan to solve the task.
        2. Post project review isn't needed.
        3. Revise the plan based on feedback from admin and quality_assurance.
        4. The plan should include the various team members,  explain which step is performed by whom, for instance: the Developer should write code, the Executor should execute code, important do not include the admin in the tasks e.g ask the admin to research.
        5. Do not show appreciation in your responses, say only what is necessary.
        6. The final message should include an accurate answer to the user request
        """,
        model_client=model_client,
        description="""Call this Agent if:
            You need to build a plan.
            DO NOT CALL THIS AGENT IF:
            You need to execute the code.""",
        model_client_stream=True,
    )

    # Code execution agent using a local command-line executor
    work_dir = os.getenv("CODE_EXECUTION_WORK_DIR", "research_workspace")
    local_executor = LocalCommandLineCodeExecutor(work_dir=work_dir)
    executor = CodeExecutorAgent(
        name="Executor",
        code_executor=local_executor,
        description=(
            "Executes code blocks (python/bash) produced by Developer and reports results."
        ),
        supported_languages=["python", "bash", "sh", "shell"],
        model_client_stream=True,
    )

    # Web search tool using gpt-4o-search-preview
    async def web_search_func(prompt: str) -> str:
        response = await web_search_client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""

    web_search_tool = FunctionTool(
        web_search_func, description="Search the web for information."
    )

    web_search_agent = AssistantAgent(
        name="Web_search_agent",
        system_message="""You are a web search agent. You search the web for information.""",
        model_client=model_client,
        description="""Call this Agent if:
            You need to search the web for information.""",
        tools=[web_search_tool],
        model_client_stream=True,
    )

    quality_assurance = AssistantAgent(
        name="Quality_assurance",
        system_message="""You are an AI Quality Assurance. Follow these instructions:
        1. Double check the plan,
        2. if there's a bug or error suggest a resolution
        3. If the task is not solved, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach.""",
        model_client=model_client,
        model_client_stream=True,
    )

    report_writer = AssistantAgent(
        name="Report_writer",
        system_message="""Look at the message history. Case 1 -- The research has been concluded successfully: the research has been done, you write the final report regarding the task and the result of the research run. Make sure to include sources from the web search (if he was called). Then terminate. Case 2 -- The research has not been concluded yet: Yield back to the Planner.""",
        model_client=model_client,
        description="""Call this agent if the research is done and we want to terminate.""",
        model_client_stream=True,
    )

    # Hierarchical group chat with allowed transitions graph
    allowed_transitions = {
        "user": ["Planner"],
        "User_proxy": ["Planner", "Quality_assurance", "Web_search_agent"],
        "Planner": [
            "User_proxy",
            "Developer",
            "Quality_assurance",
            "Web_search_agent",
            "Report_writer",
        ],
        "Developer": ["Executor", "Quality_assurance", "User_proxy", "Web_search_agent"],
        "Executor": ["Developer"],
        "Quality_assurance": [
            "Planner",
            "Developer",
            "Executor",
            "User_proxy",
            "Report_writer",
        ],
        "Web_search_agent": ["Planner", "Developer", "Executor", "User_proxy"],
        "Report_writer": ["Planner", "User_proxy"],
    }

    # Build participants list (conditionally include user_proxy if provided)
    participants = [
        developer,
        planner,
        executor,
        quality_assurance,
        web_search_agent,
        report_writer,
    ]

    if user_proxy is not None:
        participants.insert(0, user_proxy)  # Add at beginning for priority

    selector_prompt = (
        "These are the participants: {participants}. "
        "The history of the conversation is: {history}. "
        "ONLY call the User_proxy when all the agents agree that the task has been completed."
    )

    team = HierarchicalGroupChat(
        allowed_transitions=allowed_transitions,
        participants=participants,
        termination_condition=MaxMessageTermination(max_messages=max_messages),
        model_client=model_client,
        selector_prompt=selector_prompt,
    )

    user_control = UserControlAgent(name="UserController")

    return ResearchContext(
        team=team,
        user_control=user_control,
        participant_names=[agent.name for agent in participants],
    )


def get_initial_topic() -> str:
    """Get the initial research topic."""
    return INITIAL_TOPIC
