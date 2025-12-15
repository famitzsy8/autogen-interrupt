# The MCP Server Setup

This is the MCP server setup that is used by the agents in `../agentServer`. It supports the agents' access to various aspects of the Congress API and the retrieval of relevant sections of a bill (see Section 5.2). We have the following files and directories:

- `main.py`: Contains the main MCP server functions' logic, and running this file starts the entire MCP server
- `main_test.py`: A copy of `main.py` but instead of starting the server, it runs tests that the functions inside `main.py` are working correctly.

- `util/`: Contains all the helper functions we use to keep more complex logic away from the main file
- `rag/`: Contains the entire Retrieval-Augmented Generation (RAG) setup that is used to retrieve the relevant sections of a bill (for now)
- `data/`: Contains additional data that is used to power the MCP functions

## Filling in the secrets.ini file

For the Congress MCP server to work completely, we need API keys for the following services:

- OpenAI (for textual embeddings and LLM generation)
- Congress API (for all the legislative histories of the bills)
- Govinfo.gov (for structured access to the Congressional Record)
- (Optional) Langchain API (to remotely log the retrieval runs)

You can get them here:

- [Congress API](https://api.congress.gov/sign-up/)
- [GovInfo API](https://www.govinfo.gov/api-signup)
- [OpenAI API](https://platform.openai.com/api-keys)
- [Langchain API](https://smith.langchain.com/)

Note: The Congress API as well as the GovInfo API are free of charge, the OpenAI API is billed per usage.

