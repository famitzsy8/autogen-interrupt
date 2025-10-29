"""Interactive CLI for deep research with interrupt capabilities.

This script extends dr_autogen.py by adding human-in-the-loop interruption capabilities
using UserControlAgent. While the research runs, you can press 'i' to pause the conversation,
compose a message, and send it to a specific agent.

Usage:
    python dr_interrupt.py

Commands while running:
    i - interrupt the conversation, author a message, and send it to an agent
    q - quit the CLI loop once the current conversation finishes
"""

from __future__ import annotations

import asyncio
import configparser
import contextlib
from dataclasses import dataclass
from typing import Iterable

from autogen_agentchat.agents import UserProxyAgent, AssistantAgent, CodeExecutorAgent
from autogen_agentchat.agents._user_control_agent import UserControlAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import (
    BaseChatMessage,
    BaseAgentEvent,
    ToolCallRequestEvent,
    ToolCallExecutionEvent,
    CodeGenerationEvent,
    CodeExecutionEvent,
    SelectorEvent,
    ModelClientStreamingChunkEvent,
    UserInputRequestedEvent,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from _hierarchical_groupchat import HierarchicalGroupChat
from openai import AsyncOpenAI

from autogen_core.tools import FunctionTool

config = configparser.ConfigParser()
config.read('/Users/tofixjr/Desktop/Thesis/autogen-interrupt/secrets.ini')
api_key = config['API_KEYS']['OPENAI_API_KEY']

INITIAL_TOPIC = "I want to know which professors are most key in the selection process for the Cogmaster in Paris."


@dataclass
class ResearchContext:
    """Holds reusable objects for the research team and CLI loop."""

    team: HierarchicalGroupChat
    user_control: UserControlAgent
    participant_names: list[str]


def build_research_team() -> ResearchContext:
    """Create the research agents, group chat, and control helpers."""

    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=api_key,
    )

    web_search_client = AsyncOpenAI(api_key=api_key)

    # Human-in-the-loop admin using new UserProxyAgent API.
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
        model_client_stream=True
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
        model_client_stream=True
    )

    # Code execution agent using a local command-line executor.
    local_executor = LocalCommandLineCodeExecutor(work_dir="dream")
    executor = CodeExecutorAgent(
        name="Executor",
        code_executor=local_executor,
        description=(
            "Executes code blocks (python/bash) produced by Developer and reports results."
        ),
        supported_languages=["python", "bash", "sh", "shell"],
        model_client_stream=True
    )

    async def web_search_func(prompt: str) -> str:
        response = await web_search_client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""

    web_search_tool = FunctionTool(web_search_func, description="Search the web for information.")

    web_search_agent = AssistantAgent(
        name="Web_search_agent",
        system_message="""You are a web search agent. You search the web for information.""",
        model_client=model_client,
        description="""Call this Agent if:
            You need to search the web for information.""",
        tools=[web_search_tool],
        model_client_stream=True
    )

    quality_assurance = AssistantAgent(
        name="Quality_assurance",
        system_message="""You are an AI Quality Assurance. Follow these instructions:
        1. Double check the plan,
        2. if there's a bug or error suggest a resolution
        3. If the task is not solved, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach.""",
        model_client=model_client,
        model_client_stream=True
    )

    report_writer = AssistantAgent(
        name="Report_writer",
        system_message="""Look at the message history. Case 1 -- The research has been concluded successfully: the research has been done, you write the final report regarding the task and the result of the research run. Make sure to include sources from the web search (if he was called). Then terminate. Case 2 -- The research has not been concluded yet: Yield back to the Planner.""",
        model_client=model_client,
        description="""Call this agent if the research is done and we want to terminate.""",
        model_client_stream=True
    )

    allowed_transitions = {
        'user': ['User_proxy', 'Planner'],
        'User_proxy': ['Planner', 'Quality_assurance', 'Web_search_agent'],
        'Planner': ['User_proxy', 'Developer', 'Quality_assurance', 'Web_search_agent', 'Report_writer'],
        'Developer': ['Executor', 'Quality_assurance', 'User_proxy', 'Web_search_agent'],
        'Executor': ['Developer'],
        'Quality_assurance': ['Planner', 'Developer', 'Executor', 'User_proxy', 'Report_writer'],
        'Web_search_agent': ['Planner', 'Developer', 'Executor', 'User_proxy'],
        'Report_writer': ['Planner', 'User_proxy'],
    }

    participants = [user_proxy, developer, planner, executor, quality_assurance, web_search_agent, report_writer]
    selector_prompt = "These are the participants: {participants}. The history of the conversation is: {history}. I am the User_proxy, only involve me before we plan to do a web search."

    team = HierarchicalGroupChat(
        allowed_transitions=allowed_transitions,
        participants=participants,
        termination_condition=MaxMessageTermination(max_messages=20),
        model_client=model_client,
        selector_prompt=selector_prompt,
    )

    user_control = UserControlAgent(name="UserController")

    return ResearchContext(
        team=team,
        user_control=user_control,
        participant_names=[agent.name for agent in participants],
    )


async def research_stream(ctx: ResearchContext) -> None:
    """Stream research messages while servicing interactive CLI commands."""

    total_messages = 0
    streaming_chunks = []  # Track streaming chunks to finalize properly
    user_proxy_active = False  # Track when UserProxyAgent is waiting for input

    print("🔬 Starting deep research investigation...")
    print("Participants: " + " | ".join(ctx.participant_names))
    print("Type 'i' then Enter to interrupt, 'q' to exit the CLI loop.\n")
    print(f"Initial topic: {INITIAL_TOPIC}\n")

    print("DEBUG: Creating stream...")
    stream = ctx.team.run_stream(task=INITIAL_TOPIC)
    print("DEBUG: Stream created, getting first message...")
    message_task = asyncio.create_task(stream.__anext__())

    # Don't create command_task yet - wait for first message
    command_task: asyncio.Task[str] | None = None
    quit_requested = False
    first_message_received = False

    try:
        while True:
            pending: set[asyncio.Task[object]] = {message_task}
            # Only monitor command_task if it exists and UserProxyAgent is not active
            if command_task is not None and not user_proxy_active:
                pending.add(command_task)  # type: ignore[arg-type]

            print(f"DEBUG: Waiting on {len(pending)} tasks...")
            done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            print(f"DEBUG: Got {len(done)} completed tasks")

            # Create command_task after first message if not exists
            if not first_message_received and message_task in done:
                first_message_received = True
                if command_task is None:
                    print("DEBUG: Creating command task after first message...")
                    command_task = asyncio.create_task(
                        _read_input("Command (i interrupt / q quit): ")
                    )

            if message_task in done:
                try:
                    message = message_task.result()
                except StopAsyncIteration:
                    # Cancel command_task when stream ends
                    if command_task is not None and not command_task.done():
                        command_task.cancel()
                    break

                # Handle streaming chunks separately - no newline, immediate flush
                if isinstance(message, ModelClientStreamingChunkEvent):
                    print(message.content, end="", flush=True)
                    streaming_chunks.append(message.content)
                    message_task = asyncio.create_task(stream.__anext__())
                    continue

                # Finalize streaming output with newline if we were streaming
                if streaming_chunks:
                    print()  # Add newline after streaming completes
                    streaming_chunks.clear()

                # Display chat messages
                if isinstance(message, BaseChatMessage):
                    total_messages += 1
                    print(f"[{total_messages}] [{message.source}]: {message.content}")
                    print("-" * 40)

                    # Check if we've received input from UserProxyAgent
                    # When user_proxy_active is True and we get a message from User_proxy,
                    # it means the user has provided input
                    if user_proxy_active and message.source == "User_proxy":
                        # UserProxyAgent has received input, re-enable command monitoring
                        user_proxy_active = False
                        if command_task is None:
                            command_task = asyncio.create_task(
                                _read_input("Command (i interrupt / q quit): ")
                            )

                # Display tool calls
                elif isinstance(message, ToolCallRequestEvent):
                    print(f"\n[{message.source}] 🔧 Tool calls:")
                    for tool_call in message.content:
                        print(f"  - {tool_call.name}({tool_call.arguments})")

                # Display tool execution results
                elif isinstance(message, ToolCallExecutionEvent):
                    print(f"\n[{message.source}] ✓ Tool execution results:")
                    for result in message.content:
                        print(f"  - {result.content[:200]}...")

                # Display code generation
                elif isinstance(message, CodeGenerationEvent):
                    print(f"\n[{message.source}] 💻 Generated code (attempt {message.retry_attempt + 1}):")
                    for block in message.code_blocks:
                        print(f"  Language: {block.language}")
                        print(f"  Code:\n{block.code}")

                # Display code execution
                elif isinstance(message, CodeExecutionEvent):
                    print(f"\n[{message.source}] ▶️  Code execution (attempt {message.retry_attempt + 1}):")
                    print(f"  Exit code: {message.result.exit_code}")
                    print(f"  Output: {message.result.output[:500]}")

                # Display selector events
                elif isinstance(message, SelectorEvent):
                    print(f"\n[{message.source}] 🎯 Selector: {message.content}")

                # Check for stop reason
                elif hasattr(message, "stop_reason"):
                    print(f"🏁 Stream ended: {message.stop_reason}")
                    # Cancel command_task when stream ends
                    if command_task is not None and not command_task.done():
                        command_task.cancel()
                    break

                # Handle UserProxyAgent input requests
                elif isinstance(message, UserInputRequestedEvent):
                    print(f"\n💬 [{message.source}] is requesting input from the human user.")
                    print("Please provide your response (UserProxyAgent is waiting for input):")
                    # Cancel command_task while UserProxyAgent waits for input
                    if command_task is not None and not command_task.done():
                        command_task.cancel()
                        command_task = None
                    user_proxy_active = True

                # Generic fallback for other events
                elif isinstance(message, BaseAgentEvent):
                    print(f"\n[{message.source}] {type(message).__name__}: {message.to_text()[:200]}")
                else:
                    print("yeehaw")

                message_task = asyncio.create_task(stream.__anext__())

            if command_task is not None and command_task in done:
                command_task, quit_requested = await _process_command_task(
                    ctx, command_task, quit_requested
                )
    except asyncio.CancelledError:
        raise
    finally:
        for task in (message_task, command_task):
            if task is not None and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task


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


async def _read_input(prompt: str) -> str:
    return await asyncio.to_thread(input, prompt)


async def _process_command_task(
    ctx: ResearchContext,
    command_task: asyncio.Task[str],
    quit_requested: bool,
) -> tuple[asyncio.Task[str] | None, bool]:
    """Handle the completion of a pending CLI command task."""

    next_quit = quit_requested

    try:
        raw_command = command_task.result()
    except asyncio.CancelledError:
        return None, next_quit
    except (EOFError, KeyboardInterrupt):
        print("\nExiting CLI input loop.")
        return None, True
    except Exception as exc:
        print(f"⚠️ Command input failed: {exc}")
        if next_quit:
            return None, next_quit
        return asyncio.create_task(_read_input("Command (i interrupt / q quit): ")), next_quit

    command = raw_command.strip().lower()

    if command == "q":
        print("Requested CLI shutdown. Conversation will end once current stream completes.")
        next_quit = True
    elif command == "i":
        await _handle_interrupt(ctx)
    elif command:
        print("Unknown command. Use 'i' or 'q'.")
    else:
        print("Unknown command. Use 'i' or 'q'.")

    if next_quit:
        return None, next_quit

    return asyncio.create_task(_read_input("Command (i interrupt / q quit): ")), next_quit


async def _handle_interrupt(ctx: ResearchContext) -> None:
    """Pause the conversation, collect user input, and deliver the message."""

    print("⏸️ Pausing conversation so you can inject a message...")
    try:
        await ctx.user_control.interrupt(ctx.team)
    except Exception as exc:
        print(f"⚠️ Failed to pause the conversation: {exc}")
        return

    print("Available agents:")
    for idx, name in enumerate(ctx.participant_names, start=1):
        print(f"  {idx}. {name}")

    target = await _prompt_for_target(ctx.participant_names)
    message = await _prompt_for_interrupt_message()

    if message is None:
        print("Interrupt cancelled; resuming conversation without sending a message.")
        with contextlib.suppress(Exception):
            await ctx.team.resume()
        return

    try:
        result = await ctx.user_control.send(ctx.team, message, target)
    except Exception as exc:
        print(f"⚠️ Failed to deliver interrupt to {target}: {exc}")
        with contextlib.suppress(Exception):
            await ctx.team.resume()
        return

    if result and getattr(result, "messages", None):
        print("📨 Responses to your interrupt:")
        for response in result.messages:
            if hasattr(response, "content") and hasattr(response, "source"):
                print(f"[{response.source}]: {response.content}")
        print("-" * 40)


async def _prompt_for_interrupt_message() -> str | None:
    """Prompt the user for an interrupt message, retrying on empty input."""

    while True:
        try:
            message = await asyncio.to_thread(input, "Your interrupt message: ")
        except (EOFError, KeyboardInterrupt):
            return None

        if message and message.strip():
            return message

        print("Message cannot be empty. Please enter text or press Ctrl+C to cancel.")


async def main() -> None:
    ctx = build_research_team()
    await research_stream(ctx)
    print("✅ dr_interrupt session finished.")


if __name__ == "__main__":
    asyncio.run(main())
