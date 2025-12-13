This is the main directory of the Bachelor's thesis, the other directories correspond to previous experiments.

This directory is split into 3 parts:

- `backend/`: Contains all the logic to build an AutoGen agent team dynamically, and stream it to the interface frontend via a WebSocket + FastAPI setup

- `frontend/`: Visual interface for multi-agent communication of AutoGen agent teams. Compatible only with the 2 specific agent teams used in the thesis

- `mcp/`: Directory that harbors all the MCP servers that the AutoGen agents have access to. In our case, it is the Congress MCP server under the name `ragMCP`


Each of those repositories is containerized with Docker, and can be started using Docker Compose:

1. `docker compose up --build`

This starts all of the 3 Docker containers and makes the entire setup run.
