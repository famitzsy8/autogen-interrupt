import asyncio
import os
import logging
from pydantic import BaseModel, Field
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import UserMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the schema we want to test (copied from _analysis_service.py)
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

async def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables.")
        # Try to load from .env file if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.environ.get("OPENAI_API_KEY")
        except ImportError:
            pass
            
    if not api_key:
        logger.error("Still no OPENAI_API_KEY found. Please set it.")
        return

    logger.info("Initializing OpenAIChatCompletionClient...")
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=api_key,
    )

    prompt = """
    Analyze the following text and score it based on these criteria:
    - clarity: How clear is the text?
    - brevity: Is it concise?
    
    Text: "The quick brown fox jumps over the lazy dog."
    
    Score 1-10. Provide reasoning.
    """

    logger.info("Sending request with structured output...")
    try:
        response = await model_client.create(
            messages=[UserMessage(content=prompt, source="user")],
            json_output=AnalysisScoresStructured
        )
        
        logger.info("Response received!")
        logger.info(f"Raw content type: {type(response.content)}")
        logger.info(f"Raw content: {response.content}")

        # Parse the JSON string into the model
        try:
            if isinstance(response.content, str):
                parsed_content = AnalysisScoresStructured.model_validate_json(response.content)
                logger.info("✅ Successfully parsed string into AnalysisScoresStructured model")
            elif isinstance(response.content, AnalysisScoresStructured):
                parsed_content = response.content
                logger.info("✅ Response was already AnalysisScoresStructured model")
            else:
                logger.warning(f"❌ Unexpected content type: {type(response.content)}")
                return

            logger.info(f"Scores: {[s.model_dump() for s in parsed_content.component_scores]}")
            logger.info(f"Reasoning: {[r.model_dump() for r in parsed_content.component_reasoning]}")
            
        except Exception as e:
            logger.error(f"❌ Failed to parse response content: {e}")

    except Exception as e:
        logger.error(f"❌ Error during structured output generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
