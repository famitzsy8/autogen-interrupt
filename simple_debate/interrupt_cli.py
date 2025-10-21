"""Interactive CLI demo for interrupting a running AutoGen conversation.

This script adapts the ``interrupt_2_5.py`` example by replacing automatic
provocations with a simple command-line interface. While the debate runs, you
can press ``i`` (for "interrupt") to pause the conversation, compose a message,
and choose which agent should receive it.

Usage:
    python interrupt_cli.py

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

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.agents._user_control_agent import UserControlAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import UserProxyAgent


# Read API key from secrets.ini (keeps parity with the existing examples)
CONFIG = configparser.ConfigParser()
CONFIG.read("/Users/tofixjr/Desktop/Thesis/autogen-interrupt/secrets.ini")
API_KEY = CONFIG["API_KEYS"]["OPENAI_API_KEY"]


INITIAL_TOPIC = """
Simple debate: Who should win the 2025 Chilean presidential election - a left-wing candidate like Jadue or a right-wing candidate like Kast?

Jara_Supporter: Start by arguing why the left-wing candidate should win. Keep it short!
Kast_Supporter: Then argue why the right-wing candidate is better. Keep it short!
Neural_Agent: Feel free to ask questions when you're confused!
Moderate_Left: Offer pragmatic left-leaning perspectives.
Moderate_Right: Provide reasonable right-leaning solutions.

Take turns, one sentence each. NO long explanations!
""".strip()


@dataclass
class DebateContext:
    """Holds reusable objects for the debate and CLI loop."""

    team: RoundRobinGroupChat
    user_control: UserControlAgent
    participant_names: list[str]

def build_debate() -> DebateContext:
    """Create the debate agents, group chat, and control helpers."""

    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=API_KEY,
    )

    communist_agent = AssistantAgent(
        name="Jara_Supporter",
        model_client=model_client,
        description="Supporter of Daniel Jadue/left-wing candidate",
        system_message="""You are a passionate supporter of left-wing politics in Chile. You believe in:
- Strong social programs and wealth redistribution
- Workers' rights and labor unions
- Critique of neoliberal capitalism
- Support for candidates like Daniel Jadue or similar left-wing politicians

Keep your responses SHORT (1-2 sentences max). Never say TERMINATE. Reply to the others' comments. Start polite but become more aggressive and witty.""",
    )

    liberal_agent = AssistantAgent(
        name="Kast_Supporter",
        model_client=model_client,
        description="Supporter of José Antonio Kast/right-wing candidate",
        system_message="""You are a supporter of right-wing/conservative politics in Chile. You believe in:
- Free market capitalism and reduced government intervention
- Traditional values and law and order
- Support for candidates like José Antonio Kast
- Economic growth through private enterprise

Keep your responses SHORT (1-2 sentences max). Never say TERMINATE. Reply to the others' comments. Start polite but become more aggressive and witty.""",
    )

    neural_agent = AssistantAgent(
        name="Neural_Agent",
        model_client=model_client,
        description="AI agent that observes and asks clarifying questions",
        system_message="""You are an AI observing this political debate. You are a bit confused about human politics but genuinely curious. Your role is to:
- Ask innocent, clarifying questions that might seem obvious to humans
- Accidentally calm heated exchanges by changing focus to basic concepts
- Be slightly lost but well-intentioned
- Wonder about fundamental assumptions both sides make

Keep your responses SHORT (1-2 sentences max). Never say TERMINATE. Ask simple, curiosity-driven questions.""",
    )

    moderate_left_agent = AssistantAgent(
        name="Moderate_Left",
        model_client=model_client,
        description="Moderate center-left supporter with pragmatic views",
        system_message="""You are a moderate center-left supporter in Chilean politics. You believe in:
- Gradual social reform rather than radical change
- Mixed economy with both public and private sectors
- Pragmatic solutions balancing social justice with economic stability
- Democratic institutions and compromise

Keep your responses SHORT (1-2 sentences max). Never say TERMINATE. Aim for diplomatic, practical suggestions.""",
    )

    moderate_right_agent = AssistantAgent(
        name="Moderate_Right",
        model_client=model_client,
        description="Moderate center-right supporter with business-friendly views",
        system_message="""You are a moderate center-right supporter in Chilean politics. You believe in:
- Free market principles with sensible regulation
- Fiscal responsibility and gradual economic reform
- Traditional values with respect for democratic pluralism
- Business-friendly policies alongside social safety nets

Keep your responses SHORT (1-2 sentences max). Never say TERMINATE. Offer reasonable, stability-focused proposals.""",
    )
    participants = [
        communist_agent,
        liberal_agent,
        neural_agent,
        moderate_left_agent,
        moderate_right_agent,
    ]

    team = RoundRobinGroupChat(
        participants=participants,
        termination_condition=MaxMessageTermination(max_messages=20),
    )

    user_control = UserControlAgent(name="UserController")

    return DebateContext(
        team=team,
        user_control=user_control,
        participant_names=[agent.name for agent in participants],
    )


async def conversation_stream(ctx: DebateContext) -> None:
    """Stream debate messages while servicing interactive CLI commands."""

    total_messages = 0
    print("🏛️ Starting Chilean politics discussion...")
    print("Participants: " + " | ".join(ctx.participant_names))
    print("Type 'i' then Enter to interrupt, 'q' to exit the CLI loop.\n")

    stream = ctx.team.run_stream(task=INITIAL_TOPIC)
    message_task = asyncio.create_task(stream.__anext__())
    command_task: asyncio.Task[str] | None = asyncio.create_task(
        _read_input("Command (i interrupt / q quit): ")
    )
    quit_requested = False

    try:
        while True:
            pending: set[asyncio.Task[object]] = {message_task}
            if command_task is not None:
                pending.add(command_task)  # type: ignore[arg-type]

            done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

            if message_task in done:
                try:
                    message = message_task.result()
                except StopAsyncIteration:
                    break

                if hasattr(message, "content") and hasattr(message, "source"):
                    total_messages += 1
                    prefix = {
                        "Neural_Agent": "🤖",
                        "Moderate_Left": "🤝",
                        "Moderate_Right": "🤝",
                    }.get(message.source, "💬")
                    print(f"[{total_messages}] [{prefix} {message.source}]: {message.content}")
                    print("-" * 40)
                elif hasattr(message, "stop_reason"):
                    print(f"🏁 Stream ended: {message.stop_reason}")
                    break

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
            # Fall back to the first agent if input is aborted.
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
    ctx: DebateContext,
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
    except Exception as exc:  # pragma: no cover - defensive branch
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


async def _handle_interrupt(ctx: DebateContext) -> None:
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
    ctx = build_debate()
    await conversation_stream(ctx)
    print("✅ interrupt_cli session finished.")


if __name__ == "__main__":
    asyncio.run(main())
