# Factory

This directory implements a configuration-driven factory pattern for dynamically creating multi-agent teams from YAML specifications. It enables declarative agent configuration without hardcoding definitions.


## Core Files

### Team Factory (`team_factory.py`)
Main production factory for initializing agent teams with WebSocket-based user input.

Key function `init_team()`:
1. Loads YAML configuration from `team.yaml`
2. Creates model client via ModelClientFactory
3. Initializes function registries for tools and input handlers
4. Creates UserProxyAgent with WebSocket input queue
5. Builds all other agents via `build_agents()`
6. Configures plugins (StateContextPlugin for cognitive offloading)
7. Creates group chat (SelectorGroupChat or HierarchicalGroupChat)
8. Returns `AgentTeamContext` containing team and metadata

Supports template variable substitution in agent descriptions: `{company_name}`, `{bill_name}`, `{congress}`, `{agent_names}`.


### Model Client Factory (`model_client_factory.py`)
Factory for creating LLM clients supporting multiple providers (OpenAI, Anthropic). Loads configuration from `model.yaml` and manages API keys via environment variables. Uses singleton pattern for application-wide instance.


### Team Factory Demo (`team_factory_demo.py`)
Demo factory for command-line testing. Uses `team_demo.yaml`, stdin-based input instead of WebSocket, and simpler termination conditions.


## Registry Pattern

### Base Function Registry (`base_function_registry.py`)
Abstract base class for function registries. Dynamically imports modules, inspects callables, validates signatures, and stores functions with metadata.

### Function Registry (`registry.py`)
Registry for tool functions. Minimal validation - accepts sync or async functions. Discovers functions in `tool_functions.py`.

### Input Function Registry (`input_function_registry.py`)
Registry for input handler functions. Strict validation - requires async functions only. Discovers functions in `input_functions.py`.

### Tool Function Loader (`function_loader.py`)
Loader classes that retrieve specific functions by name from their respective registries.

### Input Function Loader (`input_function_loader.py`)
Loader classes that retrieve specific functions by name from their respective registries.


## Function Definitions

### Tool Functions (`tool_functions.py`)
Available Python tools for agents:
- `web_search(prompt)`: Uses GPT-4o-search-preview for web search

### Input Functions (`input_functions.py`)
Available input handlers:
- `queue_based_input()`: Wraps AgentInputQueue for WebSocket-based user input


## YAML Configuration

### Team Configuration (`team.yaml`)
Production team configuration defining:
- `agents`: Agent definitions with name, description, system_message, tools, agent_class
- `team`: Group chat configuration (mcp_url, group_chat_class, selector_prompt, allowed_transitions)
- `llm`: Model client settings
- `tasks`: Investigation task descriptions

Agent tools can be Python functions (`python_tools`) or MCP tools (`mcp_tools` with FilteredWorkbench).

### Team Demo Configuration (`team_demo.yaml`)
Simplified configuration for CLI testing.

### Model Configuration (`model.yaml`)
Model client configurations with provider (openai/anthropic), model name, and descriptions.


## Return Type

`AgentTeamContext` dataclass containing:
- `team`: The initialized BaseGroupChat
- `user_control`: UserControlAgent for programmatic control
- `participant_names`: List of agent names
- `display_names`: Mapping of agent_name to display_name
- `external_termination`: For user-initiated stops
- `state_context_plugin`: Reference to state plugin (if enabled)
