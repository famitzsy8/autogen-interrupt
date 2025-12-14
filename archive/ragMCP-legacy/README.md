# The MCP Server Setup

This is the MCP server setup that is used by the agents in `../agentServer`. We have the following files and directories:

- `main.py`: Contains the main MCP server functions' logic, and running this file starts the entire MCP server
- `main_test.py`: A copy of `main.py` but instead of starting the server, it runs tests that the functions inside `main.py` are working correctly.

- `util/`: Contains all the helper functions we use to keep more complex logic away from the main file
- `rag/`: Contains the entire Retrieval-Augmented Generation (RAG) setup that is used to retrieve the relevant sections of a bill (for now)
- `data/`: Contains additional data that is used to power the MCP functions