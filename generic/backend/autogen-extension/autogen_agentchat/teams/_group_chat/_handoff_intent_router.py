"""
HandoffIntentRouter: Detects if a user message contains an intention to change handoff logic.

This module provides two-pass intent detection:
1. Fast pattern-based detection using regex
2. LLM-based detection for nuanced cases (only when pattern fails and message is substantive)
"""

import logging
import re
from typing import List

from autogen_core.models import ChatCompletionClient, CreateResult, SystemMessage, UserMessage

logger = logging.getLogger(__name__)


class HandoffIntentRouter:

    # Detects if a user message contains intent to change handoff logic.

    #  Uses a two-pass detection strategy:
    #- Pass 1: Fast regex pattern matching
    
    #- Pass 2: LLM-based detection (only for longer messages that fail pattern matching)


    def __init__(self, model_client: ChatCompletionClient) -> None:
        self._model_client = model_client

        # Fast pattern-based detection rules (case-insensitive)
        self._intent_patterns: dict[str, List[str]] = {
            "notify_changes": [
                r"(only|just)\s+(involve|notify|call|contact)\s+me",
                r"don't\s+(involve|notify|call|contact)",
                r"stop\s+(calling|involving|notifying)",
            ],
            "conditional_routing": [
                r"if\s+\w+\s+mentioned.*call\s+\w+",
                r"when\s+\w+.*agent",
                r"(always|never)\s+(call|involve)",
            ],
            "agent_preference": [
                r"focus\s+on\s+\w+\s+agent",
                r"use\s+(more|less)\s+\w+",
                r"prioritize\s+\w+",
            ],
            "rule_changes": [
                r"from\s+now\s+on",
                r"new\s+rule",
                r"change.*agent.*selection",
            ],
        }

    async def detect_intent(self, message: str) -> bool:
        # Detect if a message contains intent to change handoff logic.

        # Two-pass detection:
        # 1. FAST: Pattern matching (regex)
        # 2. SLOW: LLM-based (only if uncertain and message is substantive)

        text_lower = message.lower()

        # PASS 1: Fast pattern matching
        if self._check_patterns(text_lower):
            logger.debug("Intent detected via pattern matching")
            return True

        # PASS 2: LLM detection for subtle cases (only for longer messages)
        if len(message) > 20:
            return await self._detect_via_llm(message)

        return False

    def _check_patterns(self, text: str) -> bool:
        # Quick regex-based pattern detection.
        for category, patterns in self._intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    logger.debug(f"Intent detected via {category}")
                    return True
        return False

    async def _detect_via_llm(self, message: str) -> bool:
        # LLM-based intent detection AFTER failing regex test
        detection_prompt = """Your task: Determine if this user message contains EXPLICIT intent to change agent selection logic or notification triggers.

                            User Message:
                            {message}

                            Respond with ONLY:
                            YES - if the user is changing when agents should be called, when to notify, special conditions, etc.
                            NO - if the user is providing feedback, research direction, or general comments.

                            YES Examples:
                            - "Only involve me when everything is ready"
                            - "From now on, if we mention Petrobras, call Quality_Assurance"
                            - "Stop calling the Web_Agent for this"

                            NO Examples:
                            - "That's good progress, keep searching"
                            - "Look for contracts from 2010"

                            Answer:"""

        try:
            response: CreateResult = await self._model_client.create(
                messages=[
                    SystemMessage(content="You are a precise intent classifier."),
                    UserMessage(
                        content=detection_prompt.format(message=message),
                        source="manager"
                    ),
                ]
            )

            # Extract content - it should be a string for this use case
            if not isinstance(response.content, str):
                logger.warning(f"Unexpected response type: {type(response.content)}, defaulting to False")
                return False

            answer = response.content.strip().upper()
            has_intent = answer.startswith("YES")

            logger.debug(f"LLM intent detection: {answer}")
            return has_intent

        except Exception as e:
            logger.warning(f"LLM intent detection failed: {e}, defaulting to False")
            return False
