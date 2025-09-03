# AutoGen Multi-Agent System and WebSocket Server

Here we have all the components that create the multi-agent system. The top logic for the agent systems are in the `investigation.py` files. Currently, we are developing the 5th iteration of the multi-agent system.

Here are the other files that make the multi-agent system work:

- `investigation`: Is where the main logic sits for the current multi-agent system (5th iteration)
- `server`: Starts the `investigation` with silent logging activated for debugging purposes. The logs can then be found in the `logs/` directory
- `wsServer`: The actual websocket server streaming the agents' output, that is then being wrapped around by `server`
- `FilteredWorkbench`: A module that allows for allocating a subset of MCP tools to specific agents

### Helper & Utilites

The `util/` files contain the `PlannerAgent` module, which is an extension to the `AssistantAgent`, which plans its queries if they are empty. Also there is the config logic to retrieve the API keys

The `/helper` files contain the most logic that handles the agent output from `investigation` and parses it.

### Secrets

A global usage of secrets is still not yet implemented. You need to create the same secrets.ini file as in the parent directory.