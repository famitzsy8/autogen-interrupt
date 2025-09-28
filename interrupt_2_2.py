"""Standalone runtime interrupt demo.

This example mirrors the new runtime-focused pytest coverage and can be
run directly when pytest is unavailable. Each scenario exercises a different
interrupt pathway and raises AssertionError if expectations are not met.
"""

import asyncio
import time
from typing import Awaitable, Callable

from autogen_core import SingleThreadedAgentRuntime
from autogen_core._closure_agent import ClosureAgent, ClosureContext
from autogen_core._default_subscription import DefaultSubscription
from autogen_core._message_context import MessageContext

from autogen_agentchat.agents import BaseChatAgent, UserControlAgent
from autogen_agentchat.base import Response
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat


class SlowAgent(BaseChatAgent):
    """Agent that blocks to expose interrupt behaviour."""

    def __init__(self, name: str) -> None:
        super().__init__(name=name, description="Slow agent for interrupt demo")
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()

    @property
    def produced_message_types(self) -> tuple[type[BaseChatMessage], ...]:
        return (TextMessage,)

    async def on_messages(self, messages: tuple[BaseChatMessage, ...], cancellation_token) -> Response:
        if not messages:
            self.cancelled.set()
            raise asyncio.CancelledError()
        self.started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            self.cancelled.set()
            raise
        return Response(chat_message=TextMessage(content="done", source=self.name))

    async def on_reset(self, cancellation_token) -> None:
        self.started.clear()
        self.cancelled.clear()


class FastAgent(BaseChatAgent):
    """Agent that responds immediately."""

    def __init__(self, name: str) -> None:
        super().__init__(name=name, description="Fast agent for fallback demo")
        self.started = asyncio.Event()

    @property
    def produced_message_types(self) -> tuple[type[BaseChatMessage], ...]:
        return (TextMessage,)

    async def on_messages(self, messages: tuple[BaseChatMessage, ...], cancellation_token) -> Response:
        self.started.set()
        return Response(chat_message=TextMessage(content="ok", source=self.name))

    async def on_reset(self, cancellation_token) -> None:
        self.started.clear()


async def demo_team_interrupt_cancels_running_work() -> None:
    print("Running: team interrupt cancels slow agent work")
    slow_agent = SlowAgent("Slow")
    team = RoundRobinGroupChat([slow_agent], termination_condition=MaxMessageTermination(5))
    user_control = UserControlAgent("controller")

    run_task = asyncio.create_task(team.run(task="begin", output_task_messages=False))
    await asyncio.wait_for(slow_agent.started.wait(), timeout=1.0)

    start = time.perf_counter()
    try:
        await user_control.interrupt(team)
    except asyncio.CancelledError:
        print("- interrupt bubbled CancelledError; suppressing for demo")
    duration = time.perf_counter() - start
    print(f"- interrupt finished in {duration:.3f}s")

    if duration >= 10.0:
        raise AssertionError("interrupt should resolve quickly")

    result = await asyncio.wait_for(run_task, timeout=1.0)
    if result.stop_reason != "USER_INTERRUPT":
        raise AssertionError(f"expected USER_INTERRUPT stop reason, saw {result.stop_reason}")
    if not slow_agent.cancelled.is_set():
        raise AssertionError("slow agent should observe cancellation")


async def demo_runtime_interrupt_cancels_queued_work() -> None:
    print("Running: runtime interrupt cancels queued work before it executes")
    runtime = SingleThreadedAgentRuntime()
    invoked = asyncio.Event()

    async def queued_handler(_ctx: ClosureContext, message: str, _mctx: MessageContext) -> str:
        invoked.set()
        return message.upper()

    await ClosureAgent.register_closure(
        runtime,
        type="queued_worker",
        closure=queued_handler,
        subscriptions=lambda: [DefaultSubscription()],
    )

    recipient = await runtime.get("queued_worker")
    send_task = asyncio.create_task(runtime.send_message("hello", recipient=recipient))

    await asyncio.sleep(0)

    start = time.perf_counter()
    await runtime.interrupt()
    duration = time.perf_counter() - start
    print(f"- runtime.interrupt() finished in {duration:.3f}s")

    runtime.start()

    try:
        await asyncio.wait_for(send_task, timeout=1.0)
    except asyncio.CancelledError:
        print("- queued send cancelled as expected")
    else:
        raise AssertionError("queued work should be cancelled by interrupt")

    await asyncio.wait_for(runtime._message_queue.join(), timeout=1.0)
    if runtime._message_queue._unfinished_tasks != 0:
        raise AssertionError("message queue should be drained after interrupt")
    if invoked.is_set():
        raise AssertionError("handler should not run once interrupted")

    await runtime.stop()


async def demo_team_interrupt_fallback_without_runtime_api() -> None:
    print("Running: team interrupt falls back when runtime API is absent")
    fast_agent = FastAgent("Fast")
    team = RoundRobinGroupChat([fast_agent], termination_condition=MaxMessageTermination(50))

    run_task = asyncio.create_task(team.run(task="go", output_task_messages=False))
    await asyncio.wait_for(fast_agent.started.wait(), timeout=1.0)

    original_interrupt = getattr(team._runtime, "interrupt", None)
    try:
        setattr(team._runtime, "interrupt", None)
        try:
            await team.interrupt()
        except asyncio.CancelledError:
            print("- fallback interrupt bubbled CancelledError; suppressing")
    finally:
        if original_interrupt is not None:
            setattr(team._runtime, "interrupt", original_interrupt)

    result = await asyncio.wait_for(run_task, timeout=1.0)
    if result.stop_reason != "USER_INTERRUPT":
        raise AssertionError("fallback interrupt should still terminate the run")


async def main() -> None:
    print("Runtime interrupt verification demos")
    print("=" * 40)

    demos: list[tuple[str, Callable[[], Awaitable[None]]]] = [
        ("team interrupt cancels slow agent", demo_team_interrupt_cancels_running_work),
        ("runtime interrupt clears queue", demo_runtime_interrupt_cancels_queued_work),
        ("team interrupt fallback", demo_team_interrupt_fallback_without_runtime_api),
    ]

    for title, handler in demos:
        print(f"\n>>> {title}")
        await handler()
        print("- ok")

    print("\nAll runtime interrupt demos completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
