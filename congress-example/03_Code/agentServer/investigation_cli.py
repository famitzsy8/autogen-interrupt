"""Interactive CLI for the congressional investigation demo with user interrupts.

This module mirrors the existing ``investigation.py`` workflow but exposes a
terminal interface similar to ``interrupt_cli.py`` so that a human can pause the
conversation and inject guidance for any agent.
"""

from __future__ import annotations

import argparse
import asyncio
import configparser
import contextlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

import investigation as investigation_module
from autogen_agentchat.agents._user_control_agent import UserControlAgent
from autogen_agentchat.base._task import TaskResult
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import BaseChatMessage, ModelClientStreamingChunkEvent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, SseServerParams

from FilteredWorkbench import FilteredWorkbench
from util.PlannerAgent import PlannerAgent
from util.config import _get_key


if not hasattr(investigation_module, "selector_logger"):
    investigation_module.selector_logger = logging.getLogger("investigation.selector")

_create_llm_selector = investigation_module._create_llm_selector
_check_agent_name_safety = investigation_module._check_agent_name_safety


LOCAL_PATH = Path(__file__).resolve().parent


@dataclass
class InvestigationContext:
    team: SelectorGroupChat
    user_control: UserControlAgent
    participant_names: list[str]
    task_prompt: str

@contextlib.asynccontextmanager
async def build_investigation_context(company_name: str, bill: str, *, year: int = 2018) -> InvestigationContext:
    """Build the investigation agents, chat team, and supporting resources."""

    with open(LOCAL_PATH / "config" / "agents.yaml", "r") as f:
        agents_cfg = yaml.safe_load(f)
    with open(LOCAL_PATH / "config" / "tasks.yaml", "r") as f:
        tasks_cfg = yaml.safe_load(f)
    with open(LOCAL_PATH / "config" / "prompt.yaml", "r") as f:
        prompt_cfg = yaml.safe_load(f)

    try:
        oai_key = _get_key("OPENAI_API_KEY")
    except Exception as exc:  # pragma: no cover - defensive fallback
        print(f"⚠️  API key loading failed: {exc}")
        config = configparser.ConfigParser()
        for candidate in ("/app/secrets.ini", "/app/agentServer/secrets.ini", "secrets.ini"):
            if os.path.exists(candidate):
                config.read(candidate)
                with contextlib.suppress(KeyError):
                    oai_key = config["API_KEYS"]["OPENAI_API_KEY"]
                    print(f"✅ Found API key in {candidate}")
                    break
        else:  # pragma: no cover - defensive branch
            raise RuntimeError("Could not locate an OpenAI API key")

    model_client = OpenAIChatCompletionClient(model="gpt-4.1-mini", api_key=oai_key)

    ragmcp_base_url = os.getenv("RAGMCP_URL", "http://ragmcp:8080")
    params = SseServerParams(url=f"{ragmcp_base_url}/sse", timeout=60)

    stack = contextlib.AsyncExitStack()
    await stack.__aenter__()
    try:
        workbench = await stack.enter_async_context(McpWorkbench(server_params=params))

        allowed_tool_names_orchestrator = ["getBillSummary"]
        allowed_tool_names_comm = ["get_committee_members", "get_committee_actions", "getBillCommittees"]
        allowed_tool_names_bill = [
            "getBillSponsors",
            "getBillCoSponsors",
            "getBillCommittees",
            "getRelevantBillSections",
            "getBillSummary",
        ]
        allowed_tool_names_actions = ["extractBillActions", "get_committee_actions"]
        allowed_tool_names_amendments = [
            "getAmendmentSponsors",
            "getAmendmentCoSponsors",
            "getBillAmendments",
            "getAmendmentText",
            "getAmendmentActions",
        ]
        allowed_tool_names_congress_members = [
            "getCongressMemberName",
            "getCongressMemberParty",
            "getCongressMemberState",
            "getBillSponsors",
            "getBillCoSponsors",
        ]

        workbench_comm = FilteredWorkbench(workbench, allowed_tool_names_comm)
        workbench_bill = FilteredWorkbench(workbench, allowed_tool_names_bill)
        workbench_actions = FilteredWorkbench(workbench, allowed_tool_names_actions)
        workbench_amendments = FilteredWorkbench(workbench, allowed_tool_names_amendments)
        workbench_congress_members = FilteredWorkbench(workbench, allowed_tool_names_congress_members)
        workbench_orchestrator = FilteredWorkbench(workbench, allowed_tool_names_orchestrator)

        termination_condition = TextMentionTermination("TERMINATE")

        selected_agent_names = [
            "committee_specialist",
            "bill_specialist",
            "orchestrator",
            "actions_specialist",
            "amendment_specialist",
            "congress_member_specialist",
        ]

        committee_specialist = PlannerAgent(
            name="committee_specialist",
            description=agents_cfg["committee_specialist"]["description"].format(
                agent_names=selected_agent_names,
                company_name=company_name,
            ),
            model_client=model_client,
            workbench=workbench_comm,
            model_client_stream=True,
            reflect_on_tool_use=True,
        )
        bill_specialist = PlannerAgent(
            name="bill_specialist",
            description=agents_cfg["bill_specialist"]["description"].format(
                bill=bill,
                agent_names=selected_agent_names,
                company_name=company_name,
            ),
            model_client=model_client,
            workbench=workbench_bill,
            model_client_stream=True,
            reflect_on_tool_use=True,
        )
        actions_specialist = PlannerAgent(
            name="actions_specialist",
            description=agents_cfg["actions_specialist"]["description"].format(
                agent_names=selected_agent_names,
                company_name=company_name,
            ),
            model_client=model_client,
            workbench=workbench_actions,
            model_client_stream=True,
            reflect_on_tool_use=True,
        )
        amendment_specialist = PlannerAgent(
            name="amendment_specialist",
            description=agents_cfg["amendment_specialist"]["description"].format(
                agent_names=selected_agent_names,
                company_name=company_name,
            ),
            model_client=model_client,
            workbench=workbench_amendments,
            model_client_stream=True,
            reflect_on_tool_use=True,
        )
        congress_member_specialist = PlannerAgent(
            name="congress_member_specialist",
            description=agents_cfg["congress_member_specialist"]["description"].format(
                agent_names=selected_agent_names,
                company_name=company_name,
            ),
            model_client=model_client,
            workbench=workbench_congress_members,
            model_client_stream=True,
            reflect_on_tool_use=True,
        )

        agents = [
            committee_specialist,
            bill_specialist,
            actions_specialist,
            amendment_specialist,
            congress_member_specialist,
        ]
        agent_names = [agent.name for agent in agents]

        orchestrator = PlannerAgent(
            name="orchestrator",
            description=agents_cfg["orchestrator"]["description"].format(
                bill=bill,
                agent_names=agent_names,
                company_name=company_name,
            ),
            model_client=model_client,
            model_client_stream=True,
            workbench=workbench_orchestrator,
        )
        agents.append(orchestrator)

        llm_selector = _create_llm_selector(
            agent_names=[a.name for a in agents],
            prompt_cfg=prompt_cfg,
            oai_key=oai_key,
        )

        if not _check_agent_name_safety(agent_names):
            raise ValueError("Agent names are not safe to use in the selector function.")

        team = SelectorGroupChat(
            agents,
            termination_condition=termination_condition,
            selector_func=llm_selector,
            model_client=model_client,
            max_turns=150,
        )

        user_control = UserControlAgent(name="UserController")
        task_prompt = tasks_cfg["main_task"]["description"].format(
            year=year,
            bill_name=bill,
            company_name=company_name,
        )

        context = InvestigationContext(
            team=team,
            user_control=user_control,
            participant_names=[agent.name for agent in agents],
            task_prompt=task_prompt,
        )

        yield context
    finally:
        await stack.aclose()


async def conversation_stream(ctx: InvestigationContext) -> None:
    """Stream investigation messages while servicing interactive CLI commands."""

    print("🧭 Starting congressional investigation...")
    print("Participants: " + " | ".join(ctx.participant_names))
    print("Type 'i' then Enter to interrupt, 'q' to exit the CLI loop.\n")

    stream = ctx.team.run_stream(task=ctx.task_prompt)
    message_task = asyncio.create_task(stream.__anext__())
    command_task: asyncio.Task[str] | None = asyncio.create_task(
        _read_input("Command (i interrupt / q quit): ")
    )
    quit_requested = False
    display_counter = 0
    active_streams: dict[str, dict[str, Any]] = {}

    def _register_stream_key(state: dict[str, Any], key: str | None) -> None:
        if key is None:
            return
        active_streams[key] = state
        state.setdefault("keys", set()).add(key)

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

                if isinstance(message, ModelClientStreamingChunkEvent):
                    stream_key = message.full_message_id or message.id
                    state = active_streams.get(stream_key)
                    if state is None:
                        display_counter += 1
                        state = {
                            "index": display_counter,
                            "source": message.source,
                            "chunks": [],
                        }
                        _register_stream_key(state, stream_key)
                        print(f"[{state['index']}] [{message.source}]: ", end="", flush=True)
                        state["header_printed"] = True
                    _register_stream_key(state, message.id)
                    _register_stream_key(state, message.full_message_id)
                    state.setdefault("chunks", []).append(message.content)
                    print(message.content, end="", flush=True)
                    message_task = asyncio.create_task(stream.__anext__())
                    continue

                if isinstance(message, BaseChatMessage):
                    state = active_streams.get(message.id)
                    if state is None:
                        display_counter += 1
                        index = display_counter
                        print(f"[{index}] [{message.source}]: {message.content}")
                    else:
                        buffered = "".join(state.get("chunks", []))
                        if not state.get("header_printed"):
                            print(f"[{state['index']}] [{message.source}]: ", end="", flush=True)
                            state["header_printed"] = True
                        remainder = message.content
                        if buffered and remainder.startswith(buffered):
                            remainder = remainder[len(buffered) :]
                        if remainder:
                            print(remainder, end="", flush=True)
                        print()
                        for key in list(state.get("keys", [])):
                            active_streams.pop(key, None)
                        print("-" * 60)
                        message_task = asyncio.create_task(stream.__anext__())
                        continue

                    print("-" * 60)
                    message_task = asyncio.create_task(stream.__anext__())
                    continue

                if isinstance(message, TaskResult):
                    stop_reason = message.stop_reason or "Task completed"
                    print(f"🏁 Stream ended: {stop_reason}")
                    break

            if command_task is not None and command_task in done:
                command_task, quit_requested = await _process_command_task(
                    ctx, command_task, quit_requested
                )
                if quit_requested and command_task is None:
                    # We're waiting for the conversation to end naturally.
                    print("Waiting for the conversation to finish...")
    except asyncio.CancelledError:
        raise
    finally:
        for task in (message_task, command_task):
            if task is not None and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    print("✅ investigation_cli session finished.")


async def _read_input(prompt: str) -> str:
    return await asyncio.to_thread(input, prompt)


async def _process_command_task(
    ctx: InvestigationContext,
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


async def _handle_interrupt(ctx: InvestigationContext) -> None:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the investigation CLI with user interrupts.")
    parser.add_argument("company", help="Target company for the investigation")
    parser.add_argument("bill", help="Bill identifier (e.g., s383-116)")
    parser.add_argument("--year", type=int, default=2018, help="Legislative session year for the prompt context")
    return parser.parse_args()


async def run_cli(company: str, bill: str, year: int) -> None:
    async with build_investigation_context(company, bill, year=year) as ctx:
        await conversation_stream(ctx)


def main() -> None:
    args = argparse.Namespace()
    args.company = "ExxonMobil"
    args.bill = "s383-116"
    args.year = 2018
    asyncio.run(run_cli(args.company, args.bill, args.year))


if __name__ == "__main__":
    main()
