"""
Service for parsing analysis prompts and scoring messages against watchlist criteria.

This service uses an LLM (gpt-4o-mini) to:
1. Parse user's free-form analysis descriptions into structured components
2. Score agent messages against these components for accuracy and consistency
"""

from __future__ import annotations
import json
import logging
from typing import Any

from autogen_core.models import ChatCompletionClient, UserMessage
from pydantic import BaseModel, Field

from ._models import AnalysisComponent, ComponentScore, get_analysis_component_color

logger = logging.getLogger(__name__)


class ScoreItem(BaseModel):
    label: str = Field(description="The component label")
    score: int = Field(description="The score (1-10)")

class ReasoningItem(BaseModel):
    label: str = Field(description="The component label")
    reasoning: str = Field(description="The reasoning for the score")

class AnalysisScoresStructured(BaseModel):
    """Structured schema for OpenAI output (uses lists to support dynamic keys)."""
    # OpenAI Structured Outputs do not support dict with dynamic keys (additionalProperties).
    # We must use lists of objects.
    component_scores: list[ScoreItem] = Field(
        description="List of scores for each component"
    )
    component_reasoning: list[ReasoningItem] = Field(
        description="List of reasoning for each component"
    )


class AnalysisService:
    """
    Service for parsing analysis prompts and scoring messages.

    Uses gpt-4o-mini (or any ChatCompletionClient) to:
    - Extract structured watchlist components from user descriptions
    - Score agent messages against these components
    """

    def __init__(self, model_client: ChatCompletionClient) -> None:
        """
        Initialize the analysis service.

        Args:
            model_client: ChatCompletionClient instance (typically gpt-4o-mini)
        """
        self.model_client = model_client
        logger.info("AnalysisService initialized")

    async def parse_prompt(self, prompt: str) -> list[AnalysisComponent]:
        """
        Extract 2-5 structured components from user's free-form description.

        Called once at connection, before run starts. Uses LLM to parse the user's
        natural language description into structured watchlist criteria.

        Args:
            prompt: User's free-form description of what to watch for

        Returns:
            List of AnalysisComponent objects (empty list on failure)
        """
        if not prompt or not prompt.strip():
            logger.warning("Empty prompt provided to parse_prompt")
            return []

        parse_prompt_text = f"""Extract 2-5 structured criteria from this user description of what to watch for.

User description:
{prompt}

Return JSON with criteria, each having:
- label: 2-3 word kebab-case identifier (e.g., "committee-membership")
- description: 1-2 sentence explanation of what to check

Format your response as valid JSON only, no other text.
Example:
{{
  "components": [
    {{"label": "committee-membership", "description": "Verify that committee member names match API data"}},
    {{"label": "geographic-hallucination", "description": "Check if agent invents cities or districts not present in source data"}}
  ]
}}
"""

        try:
            logger.info(f"[PARSE_PROMPT] Calling LLM to parse analysis prompt ({len(prompt)} chars)")

            response = await self.model_client.create(
                messages=[UserMessage(content=parse_prompt_text, source="user")],
                # No json_output/response_format for MVP - we'll parse JSON manually
            )

            # Extract content from response
            if not response.content:
                raise ValueError("LLM returned empty response")

            content = response.content
            logger.debug(f"[PARSE_PROMPT] LLM response: {content[:200]}...")

            # Parse JSON response
            data = json.loads(content)
            components_data = data.get("components", [])

            if not components_data:
                logger.warning("[PARSE_PROMPT] No components found in LLM response")
                return []

            # Build AnalysisComponent objects with colors
            components: list[AnalysisComponent] = []
            for comp_data in components_data:
                label = comp_data.get("label", "").strip()
                description = comp_data.get("description", "").strip()

                if not label or not description:
                    logger.warning(f"[PARSE_PROMPT] Skipping invalid component: {comp_data}")
                    continue

                components.append(AnalysisComponent(
                    label=label,
                    description=description,
                    color=get_analysis_component_color(label)
                ))

            logger.info(f"[PARSE_PROMPT] Successfully extracted {len(components)} components")
            return components

        except json.JSONDecodeError as e:
            logger.error(f"[PARSE_PROMPT] JSON parsing failed: {e}")
            logger.debug(f"[PARSE_PROMPT] Invalid JSON response: {response.content if 'response' in locals() else 'N/A'}")
            return []
        except Exception as e:
            logger.error(f"[PARSE_PROMPT] Failed to parse components: {e}", exc_info=True)
            return []

    async def score_message(
        self,
        message: str,
        components: list[AnalysisComponent],
        tool_call_facts: str,
        state_of_run: str,
        trigger_threshold: int = 8
    ) -> dict[str, ComponentScore]:
        """
        Score a message against analysis components.

        Uses gpt-4o-mini to evaluate the message for accuracy and consistency
        against known facts. Returns scores (1-10) for each component, with
        reasoning only when score >= trigger_threshold.

        Args:
            message: The agent message to score
            components: List of analysis components to score against
            tool_call_facts: Accumulated facts from verified tool executions
            state_of_run: Current research context and progress
            trigger_threshold: Score threshold for including reasoning (default: 8)

        Returns:
            Dict mapping component label → ComponentScore (empty dict on failure)
        """
        if not message or not message.strip():
            logger.warning("Empty message provided to score_message")
            return {}

        if not components:
            logger.warning("No components provided to score_message")
            return {}

        # Format components as bullet list
        components_text = "\n".join([
            f"- {comp.label}: {comp.description}"
            for comp in components
        ])

        # Handle empty context with placeholders
        facts_section = tool_call_facts if tool_call_facts and tool_call_facts.strip() else "(No trusted facts yet)"
        context_section = state_of_run if state_of_run and state_of_run.strip() else "(No context yet)"

        # Create example using actual component labels
        component_labels = [comp.label for comp in components]
        example_scores = {label: 5 for label in component_labels[:2]}  # Use first 2 for example
        example_reasoning = {label: "Example reasoning" if i == 0 else ""
                            for i, label in enumerate(component_labels[:2])}

        scoring_prompt = f"""Analyze this agent message against the watchlist criteria below.

=== AGENT MESSAGE ===
{message}

=== WATCHLIST CRITERIA (score each one) ===
{components_text}

=== CONTEXT (for reference) ===
Trusted Facts: {facts_section}
Research Progress: {context_section}

IMPORTANT: You MUST score ALL and ONLY these components: {', '.join(component_labels)}

For each criterion, score 1-10 based on HOW STRONGLY the criterion is matched/triggered:
- 1-3: Criterion is NOT relevant to this message (no match)
- 4-6: Criterion is PARTIALLY relevant (weak match)
- 7-8: Criterion is CLEARLY relevant (strong match)
- 9-10: Criterion is HIGHLY relevant and the message strongly focuses on this topic

The user wants to be alerted when messages match these criteria. Higher scores = stronger match = more likely to trigger an alert.

Always include reasoning for scores >= {trigger_threshold}.
Return valid JSON with EXACTLY the component labels provided above.

Example format (using YOUR component labels):
{{
  "component_scores": {json.dumps(example_scores, indent=4)},
  "component_reasoning": {json.dumps(example_reasoning, indent=4)}
}}
"""

        try:
            # Use structured output with flattened schema
            try:
                response = await self.model_client.create(
                    messages=[UserMessage(content=scoring_prompt, source="user")],
                    json_output=AnalysisScoresStructured
                )
            except Exception:
                response = await self.model_client.create(
                    messages=[UserMessage(content=scoring_prompt, source="user")]
                )

            if not response.content:
                raise ValueError("LLM returned empty response")

            # Parse response content and normalize to {"scores": {...}} format
            if isinstance(response.content, str):
                try:
                    # Try to parse as AnalysisScoresStructured first
                    flat_model = AnalysisScoresStructured.model_validate_json(response.content)
                    raw_data = {
                        "component_scores": {item.label: item.score for item in flat_model.component_scores},
                        "component_reasoning": {item.label: item.reasoning for item in flat_model.component_reasoning}
                    }
                except Exception:
                    # Fallback to plain JSON parsing
                    raw_data = json.loads(response.content)
            elif isinstance(response.content, AnalysisScoresStructured):
                # Structured output returned Pydantic model
                raw_data = {
                    "component_scores": {item.label: item.score for item in response.content.component_scores},
                    "component_reasoning": {item.label: item.reasoning for item in response.content.component_reasoning}
                }
            else:
                # Fallback: try to parse as dict
                raw_data = response.content if isinstance(response.content, dict) else json.loads(str(response.content))

            # Normalize to {"scores": {label: {"score": int, "reasoning": str}}} format
            if "component_scores" in raw_data:
                # Flattened format - convert to nested
                # Note: raw_data["component_scores"] is now a dict because we converted it above
                scores_data = {
                    label: {
                        "score": raw_data["component_scores"].get(label, 5),
                        "reasoning": raw_data.get("component_reasoning", {}).get(label, "")
                    }
                    for label in raw_data["component_scores"].keys()
                }
            elif "scores" in raw_data:
                # Already in nested format
                scores_data = raw_data["scores"]
            else:
                # Return default scores (5/10) for all components when format is unexpected
                default_scores = {}
                for component in components:
                    default_scores[component.label] = ComponentScore(
                        score=5,
                        reasoning="Default score - unexpected response format"
                    )
                return default_scores

            if not scores_data:
                # Return default scores (5/10) for all components when LLM fails
                default_scores = {}
                for component in components:
                    default_scores[component.label] = ComponentScore(
                        score=5,
                        reasoning="Default score - analysis unavailable"
                    )
                return default_scores

            # Build ComponentScore objects
            scores: dict[str, ComponentScore] = {}
            for label, score_data in scores_data.items():
                try:
                    score_value = score_data.get("score") if isinstance(score_data, dict) else score_data.score
                    reasoning_value = score_data.get("reasoning", "") if isinstance(score_data, dict) else score_data.reasoning

                    if score_value is None:
                        continue

                    # Validate score range
                    if not (1 <= score_value <= 10):
                        score_value = max(1, min(10, score_value))

                    scores[label] = ComponentScore(
                        score=score_value,
                        reasoning=reasoning_value if reasoning_value else ""
                    )
                except Exception:
                    continue
            return scores

        except json.JSONDecodeError as e:
            logger.error(f"[SCORE_MESSAGE] JSON parsing failed: {e}")
            logger.debug(f"[SCORE_MESSAGE] Invalid JSON response: {response.content if 'response' in locals() else 'N/A'}")
            # Return default scores on JSON parsing failure
            default_scores = {}
            for component in components:
                default_scores[component.label] = ComponentScore(
                    score=5,
                    reasoning="Default score - JSON parsing failed"
                )
            return default_scores
        except Exception as e:
            logger.error(f"[SCORE_MESSAGE] Failed to score message: {e}", exc_info=True)
            # Return default scores on any failure
            default_scores = {}
            for component in components:
                default_scores[component.label] = ComponentScore(
                    score=5,
                    reasoning="Default score - analysis error"
                )
            return default_scores
