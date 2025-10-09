"""Skeleton deep research flow with a lead researcher and web-search subagents."""

import argparse
import asyncio
import random
from dataclasses import dataclass
from typing import List, Sequence

from autogen_core import AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, message_handler


@dataclass
class ResearchRequest:
    topic: str


@dataclass
class ResearchPlan:
    topic: str
    steps: List[str]


@dataclass
class SearchTask:
    topic: str
    subtopic: str


@dataclass
class EvaluatedFinding:
    subtopic: str
    finding_summary: str
    evaluation: str


class LeadResearcher(RoutedAgent):
    """Coordinates the deep-research flow by planning and delegating tasks."""

    def __init__(self, description: str, worker_ids: Sequence[AgentId]) -> None:
        super().__init__(description)
        self._worker_ids = list(worker_ids)

    @message_handler
    async def on_research_request(self, message: ResearchRequest, ctx: MessageContext) -> None:
        plan = await self._draft_plan(message.topic)
        print("\n=== Lead Researcher Plan ===")
        for step_no, step in enumerate(plan.steps, start=1):
            print(f"Step {step_no}: {step}")

        selected_workers = self._select_workers(plan)
        if not selected_workers:
            print("No available subagents to delegate research tasks.")
            return

        print("\n=== Delegating Tasks ===")
        tasks = [
            SearchTask(topic=message.topic, subtopic=subtopic)
            for subtopic in plan.steps[: len(selected_workers)]
        ]
        for agent, task in zip(selected_workers, tasks):
            print(f"Assigning '{task.subtopic}' to {agent.__repr__}")

        findings = await asyncio.gather(
            *(
                self.send_message(task, agent)
                for agent, task in zip(selected_workers, tasks)
            )
        )

        print("\n=== Aggregated Findings ===")
        for finding in findings:
            print(f"- {finding.subtopic}: {finding.finding_summary}")
            print(f"  Evaluation: {finding.evaluation}")

    def _select_workers(self, plan: ResearchPlan) -> List[AgentId]:
        desired = min(max(len(plan.steps), 1), 4, len(self._worker_ids))
        shuffled = self._worker_ids.copy()
        random.shuffle(shuffled)
        return shuffled[:desired]

    async def _draft_plan(self, topic: str) -> ResearchPlan:
        """Placeholder that fabricates a plan; replace with LLM-backed planning."""
        num_steps = random.randint(2, 4)
        steps = [
            f"Investigate perspective {i + 1} on '{topic}'"
            for i in range(num_steps)
        ]
        await asyncio.sleep(0)  # yield control to emphasize async structure
        return ResearchPlan(topic=topic, steps=steps)


class WebResearchAgent(RoutedAgent):
    """Stub agent that pretends to search the web and evaluate findings."""

    def __init__(self, description: str, index: int) -> None:
        super().__init__(description)
        self._index = index

    @message_handler
    async def on_search_task(self, message: SearchTask, ctx: MessageContext) -> EvaluatedFinding:
        await asyncio.sleep(0)  # placeholder for actual web search latency
        summary = (
            f"Agent {self._index} would search for '{message.subtopic}' and summarize key points."
        )
        evaluation = (
            f"Agent {self._index} would rate the credibility of sources for '{message.subtopic}'."
        )
        return EvaluatedFinding(
            subtopic=message.subtopic,
            finding_summary=summary,
            evaluation=evaluation,
        )


async def run(topic: str) -> None:
    runtime = SingleThreadedAgentRuntime()

    worker_ids: List[AgentId] = []
    for idx in range(4):
        name = f"web_researcher_{idx + 1}"
        await WebResearchAgent.register(
            runtime,
            name,
            lambda idx=idx: WebResearchAgent(
                description=f"Web research agent #{idx + 1}",
                index=idx + 1,
            ),
        )
        worker_ids.append(AgentId(name, "default"))

    await LeadResearcher.register(
        runtime,
        "lead_researcher",
        lambda: LeadResearcher(
            description="Lead researcher orchestrating subagents.",
            worker_ids=worker_ids,
        ),
    )

    runtime.start()
    await runtime.send_message(
        ResearchRequest(topic=topic), AgentId("lead_researcher", "default")
    )
    await runtime.stop_when_idle()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deep-research skeleton workflow.")
    parser.add_argument(
        "topic",
        nargs="?",
        default="Impacts of renewable energy adoption on urban power grids",
        help="Topic to research",
    )
    args = parser.parse_args()

    asyncio.run(run(args.topic))


if __name__ == "__main__":
    main()
