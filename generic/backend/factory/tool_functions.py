from openai import AsyncOpenAI
import os

oai_key = os.getenv("OPENAI_API_KEY")
web_search_client = AsyncOpenAI(api_key=oai_key)

async def web_search(prompt: str) -> str:
    response = await web_search_client.chat.completions.create(
        model="gpt-4o-search-preview",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content or ""

# other ideas
# get_website
# search_google