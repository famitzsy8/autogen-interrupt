"""Interactive CLI for the deep-research AutoGen pipeline with interrupt support."""

from __future__ import annotations

import asyncio
import configparser
from dataclasses import dataclass
from typing import Iterable

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent, UserProxyAgent
from autogen_agentchat.agents._user_control_agent import UserControlAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_core.tools import FunctionTool
from openai import OpenAI

from _hierarchical_groupchat import HierarchicalGroupChat


CONFIG = configparser.ConfigParser()
CONFIG.read("/Users/tofixjr/Desktop/Thesis/autogen-interrupt/secrets.ini")
API_KEY = CONFIG["API_KEYS"]["OPENAI_API_KEY"]


INITIAL_TOPIC = (
    "I want to know which professors are most key in the selection process for the Cogmaster "
    "in Paris."
)


@dataclass
class ResearchContext:
    """Holds reusable objects for the research team and CLI loop."""

    team: HierarchicalGroupChat
    user_control: UserControlAgent
    participant_names: list[str]


@dataclass
class InterruptRequest:
    """Represents a pending interrupt authored by the user."""

    target: str
    message: str


def build_research_team() -> ResearchContext:
    """Create the research agents, group chat, and control helpers."""

    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=API_KEY,
    )

    web_search_client = OpenAI(api_key=API_KEY)

    user_proxy = UserProxyAgent(
        name="User_proxy",
        description=(
            "A human admin who can approve plans and provide guidance. "
            "Call this agent for approvals, troubleshooting, or secrets/API keys."
        ),
    )

    developer = AssistantAgent(
        name="Developer",
        model_client=model_client,
        system_message="""You are an AI developer. Follow the approved plan and:
1. Write python/shell code to solve tasks.
2. Wrap code in a single code block specifying the script type.
3. Output complete code that needs no manual edits.
4. Print the exact command you expect the executor to run.
5. Avoid multiple code blocks per response.
6. Use ```bash pip install module_name``` when new deps are needed, then send full implementation code.
7. Inspect executor feedback; if errors occur, fix and resend.
8. Do not express appreciation in responses.""",
        description="Call this agent to write code; do not call it to execute code.",
    )

    planner = AssistantAgent(
        name="Planner",
        model_client=model_client,
        system_message="""You are an AI Planner. Provide a 5-step plan that:
1. Details how to solve the task.
2. Assigns steps to the appropriate teammates (not the admin).
3. Revises based on feedback from admin and Quality_assurance.
4. Omits post-project reviews.
5. Ends with an accurate answer to the user request.
Do not express appreciation.""",
        description="Call this agent to build a plan; not for executing code.",
    )

    local_executor = LocalCommandLineCodeExecutor(work_dir="dream")
    executor = CodeExecutorAgent(
        name="Executor",
        code_executor=local_executor,
        description="Executes python/bash/sh code produced by Developer and reports the result.",
        supported_languages=["python", "bash", "sh", "shell"],
    )

    async def web_search_func(prompt: str) -> str:
        response = web_search_client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""

    web_search_tool = FunctionTool(web_search_func, description="Search the web for information.")

    web_search_agent = AssistantAgent(
        name="Web_search_agent",
        system_message="You are a web search agent. You search the web for information.",
        model_client=model_client,
        description="Call this agent when web research is required.",
        tools=[web_search_tool],
    )

    quality_assurance = AssistantAgent(
        name="Quality_assurance",
        system_message="""You are AI Quality Assurance:
1. Double-check the plan.
2. Suggest fixes for bugs or errors.
3. If unsolved, analyze the problem and propose alternative approaches.""",
        model_client=model_client,
    )

    report_writer = AssistantAgent(
        name="Report_writer",
        system_message="""Review the conversation history.
- If research concluded successfully, write the final report with sources and terminate.
- Otherwise, yield back to Planner.""",
        model_client=model_client,
        description="Call this agent to deliver the final report when research concludes.",
    )

    allowed_transitions = {
        "user": ["Planner"],
        "Planner": [
            "Developer",
            "Quality_assurance",
            "Web_search_agent",
            "Report_writer",
        ],
        "Developer": ["Executor", "Quality_assurance", "Web_search_agent"],
        "Executor": ["Developer"],
        "Quality_assurance": [
            "Planner",
            "Developer",
            "Executor",
            "Report_writer",
        ],
        "Web_search_agent": ["Planner", "Developer", "Executor", ],
        "Report_writer": ["Planner"],
    }

    participants = [
        developer,
        planner,
        executor,
        quality_assurance,
        web_search_agent,
        report_writer,
    ]

    team = HierarchicalGroupChat(
        allowed_transitions=allowed_transitions,
        participants=participants,
        termination_condition=MaxMessageTermination(max_messages=20),
        model_client=model_client,
    )

    user_control = UserControlAgent(name="UserController")

    return ResearchContext(
        team=team,
        user_control=user_control,
        participant_names=[agent.name for agent in participants],
    )


async def conversation_stream(
    ctx: ResearchContext,
    done_event: asyncio.Event,
    command_queue: asyncio.Queue[InterruptRequest],
) -> None:
    """Consume and print messages from the running research session."""

    total_messages = 0
    print("🔬 Starting deep-research session...")
    print("Participants: " + " | ".join(ctx.participant_names))
    print("Type 'i' then Enter to interrupt, 'q' to exit the CLI loop.\n")

    try:
        stream = ctx.team.run_stream(task=INITIAL_TOPIC)
        async for message in stream:
            if hasattr(message, "content") and hasattr(message, "source"):
                total_messages += 1
                print(f"[{total_messages}] [{message.source}]: {message.content}")
                print("-" * 60)
            elif hasattr(message, "stop_reason"):
                print(f"🏁 Stream ended: {message.stop_reason}")
                break
            await _process_pending_interrupts(ctx, command_queue)
    except asyncio.CancelledError:
        raise
    finally:
        done_event.set()


async def cli_loop(
    ctx: ResearchContext,
    done_event: asyncio.Event,
    command_queue: asyncio.Queue[InterruptRequest],
) -> None:
    """Listen for user commands and enqueue interrupts when requested."""

    while not done_event.is_set():
        try:
            command = (await asyncio.to_thread(input, "Command (i interrupt / q quit): ")).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting CLI input loop.")
            break

        if command == "q":
            print("Requested CLI shutdown. Conversation will end once current stream completes.")
            break
        if command != "i":
            print("Unknown command. Use 'i' or 'q'.")
            continue

        print("Available agents:")
        for idx, name in enumerate(ctx.participant_names, start=1):
            print(f"  {idx}. {name}")

        target = await _prompt_for_target(ctx.participant_names)
        message = await asyncio.to_thread(input, "Your interrupt message: ")

        if not message.strip():
            print("Empty message discarded.")
            continue

        await command_queue.put(InterruptRequest(target=target, message=message))
        print("Interrupt queued; it will be delivered at the next safe moment.")


async def _process_pending_interrupts(
    ctx: ResearchContext,
    command_queue: asyncio.Queue[InterruptRequest],
) -> None:
    """Deliver any queued interrupts through the active team."""

    while True:
        try:
            request = command_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        result = None
        try:
            await ctx.user_control.interrupt(ctx.team)
            result = await ctx.user_control.send(ctx.team, request.message, request.target)
        except Exception as exc:
            print(f"⚠️ Failed to deliver interrupt to {request.target}: {exc}")
        finally:
            command_queue.task_done()

        if result and result.messages:
            print("📨 Responses to your interrupt:")
            for response in result.messages:
                if hasattr(response, "content") and hasattr(response, "source"):
                    print(f"[{response.source}]: {response.content}")
            print("-" * 40)


async def _prompt_for_target(participants: Iterable[str]) -> str:
    """Ask the user to choose which agent should receive the message."""

    participant_list = list(participants)
    name_lookup = {name.lower(): name for name in participant_list}

    while True:
        try:
            raw = await asyncio.to_thread(input, "Target agent (name or number): ")
        except (EOFError, KeyboardInterrupt):
            print("Input interrupted; defaulting to first agent.")
            return participant_list[0]

        if not raw:
            print("Please specify a target agent.")
            continue

        raw = raw.strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(participant_list):
                return participant_list[idx]
            print("Invalid number. Try again.")
            continue

        normalized = raw.lower()
        if normalized in name_lookup:
            return name_lookup[normalized]

        print("Unknown agent. Choose by number or exact name from the list above.")


async def main() -> None:
    ctx = build_research_team()
    conversation_done = asyncio.Event()

    command_queue: asyncio.Queue[InterruptRequest] = asyncio.Queue()

    conversation_task = asyncio.create_task(
        conversation_stream(ctx, conversation_done, command_queue)
    )
    cli_task = asyncio.create_task(
        cli_loop(ctx, conversation_done, command_queue)
    )

    await cli_task

    if not conversation_done.is_set():
        print("Waiting for the conversation to finish...")
        await conversation_done.wait()

    conversation_task.cancel()
    try:
        await conversation_task
    except asyncio.CancelledError:
        pass

    print("✅ dr_cli session finished.")


if __name__ == "__main__":
    asyncio.run(main())
