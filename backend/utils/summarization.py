"""
Utility functions for summarizing agent messages using OpenAI API.
"""

from __future__ import annotations
import logging
from openai import AsyncOpenAI
from typing import Optional

logger = logging.getLogger(__name__)


class MessageSummarizer:
    """
    Handles summarization of agent messages using OpenAI's API.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", system_prompt: str | None = None):
        """
        Initialize the summarizer with OpenAI API key.

        Args:
            api_key: OpenAI API key
            model: Model to use for summarization (default: gpt-4o-mini for cost efficiency)
            system_prompt: Custom system prompt for summarization (optional)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt or (
            "You are a concise summarizer. Your task is to create brief, clear summaries "
            "of agent messages in a conversation about investigating Congressional bills. "
            "Keep summaries to 1-2 sentences maximum. Focus on the key action or finding. "
            "Be specific about what the agent did or discovered."
        )

    async def summarize(self, agent_name: str, message_content: str) -> str:
        """
        Generate a summary of an agent message.

        Args:
            agent_name: Name of the agent who sent the message
            message_content: Full content of the message to summarize

        Returns:
            A concise summary of the message (1-2 sentences)
        """
        try:
            logger.info(f"[SUMMARIZE] Agent: {agent_name}, Message length: {len(message_content)} chars")

            # If message is already very short (< 150 chars), return it as-is
            if len(message_content) <= 150:
                logger.info(f"[SUMMARIZE] Message is short (<= 150 chars), returning as-is")
                return message_content

            logger.info(f"[SUMMARIZE] Message needs summarization, calling OpenAI...")
            user_prompt = f"Summarize this message in one sentence from {agent_name}:\n\n{message_content}" # TODO: come up with a good prompt to summarize the message

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent summaries
                max_tokens=500,   # Limit summary length (~1000 characters)
            )

            summary = response.choices[0].message.content
            if not summary:
                raise ValueError("OpenAI returned empty summary")

            logger.info(f"[SUMMARIZE] SUCCESS - Generated summary for {agent_name} ({len(summary)} chars): {summary[:80]}...")
            return summary.strip()

        except Exception as e:
            logger.error(f"[SUMMARIZE] FAILED - Error generating summary for {agent_name}: {e}")
            # Fallback: return first 150 characters of message with ellipsis
            fallback = message_content[:150] + "..." if len(message_content) > 150 else message_content
            logger.warning(f"[SUMMARIZE] FALLBACK - Using truncated message ({len(fallback)} chars): {fallback[:80]}...")
            return fallback


# Global summarizer instance
_summarizer: Optional[MessageSummarizer] = None


def init_summarizer(api_key: str, model: str = "gpt-4o-mini", system_prompt: str | None = None) -> None:
    """
    Initialize the global summarizer instance.

    Args:
        api_key: OpenAI API key
        model: Model to use for summarization
        system_prompt: Custom system prompt for summarization (optional)
    """
    global _summarizer
    _summarizer = MessageSummarizer(api_key=api_key, model=model, system_prompt=system_prompt)
    logger.info(f"Initialized MessageSummarizer with model: {model}")


def get_summarizer() -> MessageSummarizer:
    """
    Get the global summarizer instance.

    Returns:
        The initialized MessageSummarizer instance

    Raises:
        RuntimeError: If summarizer hasn't been initialized
    """
    if _summarizer is None:
        raise RuntimeError("Summarizer not initialized. Call init_summarizer() first.")
    return _summarizer


async def summarize_message(agent_name: str, message_content: str) -> str:
    """
    Convenience function to summarize a message using the global summarizer.

    Args:
        agent_name: Name of the agent who sent the message
        message_content: Full content of the message to summarize

    Returns:
        A concise summary of the message
    """
    summarizer = get_summarizer()
    return await summarizer.summarize(agent_name, message_content)
