# Thesis Backend

This is the backend that supports the dynamic agent team creation, and the extensions that we undertook as part of the thesis. It is made up of the following parts:


## Subdirectories

- `autogen-extension`: This repository contains the entire code for the `autogen_core` and the `autogen_agentchat` frameworks, with our modifications included


- `demo`: Contains python files that run the agent teams in the CLI for debugging purposes

- `factory`: Contains all the factory code for the agent teams, as outlined in Section 5.5.1

- `handlers`: Directory where most of the heavy logic resides: The Input Function for the `UserProxyAgent`, the session manager, the state manager for the conversation tree and the WebSocket handling of incoming and outgoing messages

- `tools`: Contains the extension of the MCP workbench module to assign agents a custom subset of MCP functions

- `utils`: Utility logic for message summarization and YAML reading for the factory

## Files

The FastAPI server is located in `main.py`. The models that we use to communicate with the frontend are located in `models.py`.

## Set Up .env

Take a look at `env.example` and fill in the values with your own API keys. An OpenAI API key can be obtained from [here](https://platform.openai.com/account/api-keys). An Anthropic API key can be obtained from [here](https://console.anthropic.com/).