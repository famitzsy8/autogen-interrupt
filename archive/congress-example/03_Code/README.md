# Codebase of the Bachelor Thesis

Currently the codebase is organized in the following manner:

## Main base

- `ragmcp`: main logic of the MCP server
- `agentServer`: Contains the multi-agent system and streaming logic for the frontend
- `frontend_demo`: A visual demonstration of the running multi-agent system *(not the implementation of the final design!)*

## Docker compose setups

- `docker-compose.yml`: The **complete and working** docker compose setup for local deployment
- `debug-mcp.yml`: Starting the MCP container only
- `debug-agents.yml`: Starting the MCP server/container and the agents container
- `debug-frontend.yml`: Starting MCP & Agents and frontend container (without actually starting the service)

## Secrets.ini Structure

- Add a `secrets.ini` file with the following structure:

```
[API_KEYS]
CONGRESS_API_KEY = ...
OPENAI_API_KEY = ...
GPO_API_KEY = ...
LANGCHAIN_API_KEY = ...
```

- `CONGRESS_API_KEY`: The API key that lets you interact with the official [U.S Congress API](https://api.congress.gov)
- `GPO_API_KEY`: The API key that lets you interact with the [GovInfo API](https://api.govinfo.gov/). Contains segments of entire editions of the Congressional record.
- `LANGCHAIN_API_KEY`: API key for LangChain. Used for our RAG pipeline inside `ragmcp/rag`
- `OPENAI_API_KEY`: API key to use OpenAI's Language Models. We use them to power the agents.