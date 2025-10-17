"""Debate team setup logic adapted from interrupt_cli.py."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.agents._user_control_agent import UserControlAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

if TYPE_CHECKING:
    from agent_input_queue import AgentInputQueue


INITIAL_TOPIC = """
Simple debate: Who should win the 2025 Chilean presidential election - a left-wing candidate like Jara or a right-wing candidate like Kast?

Take turns, one sentence each. NO long explanations!
""".strip()


@dataclass
class DebateContext:
    """Holds reusable objects for the debate and control."""

    team: RoundRobinGroupChat
    user_control: UserControlAgent
    participant_names: list[str]


def build_debate(
    api_key: str,
    max_messages: int = 40,
    agent_input_queue: AgentInputQueue | None = None
) -> DebateContext:
    """
    Create the debate agents, group chat, and control helpers.

    Preserves exact agent configurations from original CLI (system messages, model client).

    Args:
        api_key: OpenAI API key for model client
        max_messages: Maximum number of messages before termination (default: 20)
        agent_input_queue: Optional input queue for agents requiring human input (UserProxyAgent)

    Returns:
        DebateContext containing team, user control, and participant names
    """
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=api_key,
    )

    # Optional: Human fact-checker agent (only included if input_queue provided)
    fact_checker = None
    if agent_input_queue is not None:
        # Create a wrapper that includes agent name in the input request
        async def fact_checker_input(prompt: str, cancellation_token=None) -> str:
            return await agent_input_queue.get_input(
                prompt=prompt,
                cancellation_token=cancellation_token,
                agent_name="Fact_Checker"
            )

        fact_checker = UserProxyAgent(
            name="Fact_Checker",
            description=(
                "A human fact-checker who verifies outrageous or questionable claims. "
                "Call this agent when statements seem incorrect, exaggerated, or need verification."
            ),
            input_func=fact_checker_input,  # WebSocket input instead of stdin
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

    neutral_agent = AssistantAgent(
        name="Neutral_Agent",
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

    # Build participants list (conditionally include fact_checker if provided)
    participants = [
        communist_agent,
        liberal_agent,
        neutral_agent,
        moderate_left_agent,
        moderate_right_agent,
    ]

    if fact_checker is not None:
        participants.append(fact_checker)

    team = RoundRobinGroupChat(
        participants=participants,
        termination_condition=MaxMessageTermination(max_messages=max_messages),
    )

    user_control = UserControlAgent(name="UserController")

    return DebateContext(
        team=team,
        user_control=user_control,
        participant_names=[agent.name for agent in participants],
    )


def get_initial_topic() -> str:
    """Get the initial debate topic."""
    return INITIAL_TOPIC
