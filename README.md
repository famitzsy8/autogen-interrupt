# Collaborative Human–Agent Interaction: Balancing Human Interruptions and Feedback

This is the codebase for the my Bachelor's thesis at the IVIA Lab, ETH Zurich. It comprises a visual interface that allows a user to interrupt an AutoGen agent team in real-time, provide feedback for it (human-initiated interruption) and at the same time be prompted by the agents for feedback (agent-initiated feedback). This involved modifying the AutoGen library, implementing a specific interface design and connecting the agents to tool functions, including MCP servers.

## Backend

- `backend/`: Contains all the logic to build an AutoGen agent team dynamically, and stream it to the interface frontend via a WebSocket + FastAPI setup -- See Sections 5.3, 5.4 & 5.5

## Frontend

- `frontend/`: Visual interface for multi-agent communication of AutoGen agent teams. Compatible only with the 2 specific agent teams used in the thesis -- See Chapter 6

## MCP

- `mcp/`: Directory that harbors all the MCP servers that the AutoGen agents have access to. In our case, it is the Congress MCP server under the name `ragMCP` -- See Section 5.2

## How to Run

1. Make sure that you have all the .env/secrets files filled up with your API keys. The following files are crucial

- `.env` ()
- `backend/.env`
- `mcp/secrets.ini`

Detailed instructions on how to obtain the API keys are found in the subdirectories

2. (Optional) Choose the team setup you wish to run in `backend/factory/team.yaml`. The Congress team is in `backend/factory/team.yaml.congress_backup` and the Deep Research team is in `backend/factory/team.yaml.research_backup`.

3. Navigate to 03_Code and start the Docker container:

```zsh
cd 03_Code
docker compose up --build
```

4. Navigate to [localhost 5173](https://localhost:5173) and play around with the site!

## Thesis

In order to read the thesis, click [here](../04_Thesis_FinalReport/thesis.pdf).
