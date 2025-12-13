# Handlers

This directory contains the WebSocket communication layer, session management, conversation tree state, and user input handling for the multi-agent system.


## Files

### The WebSocket Handler (`websocket_handler.py`)
Primary entry point for all client-server communication. Manages WebSocket lifecycle, routes incoming messages to appropriate handlers, and orchestrates the bidirectional conversation stream between frontend and agent team.

Key responsibilities:
- Connection management and configuration message handling
- Message routing based on type (USER_INTERRUPT, USER_DIRECTED_MESSAGE, TERMINATE_REQUEST, etc.)
- Translating autogen agent events into WebSocket messages (AGENT_MESSAGE, TOOL_CALL, STATE_UPDATE, etc.)
- Conversation streaming via async bidirectional message flow
- Tree update broadcasting to all connected clients

### The Session Manager (`session_manager.py`)
Manages multi-tab/multi-connection support by maintaining session state across WebSocket connections.

Key data structure (Session dataclass):
- `session_id`: Unique conversation identifier
- `state_manager`: Conversation tree manager
- `agent_team_context`: Initialized agent team (shared across connections)
- `websockets`: Set of all connections to this session
- `analysis_service` and `active_components`: Watchlist configuration

Sessions are created on first connection and shared across tabs. Cleanup occurs after 1 hour of inactivity.

### The State Manager (`state_manager.py`)
Manages the conversation tree structure enabling multi-branch exploration and state persistence.

Key data structure (TreeNode):
- `id`, `agent_name`, `display_name`, `message`, `summary`
- `parent`, `children`: Tree structure
- `is_active`: True if on current branch
- `node_type`: "message", "tool_call", or "tool_execution"

Core operations:
- `add_node()`: Append message to current branch
- `create_branch()`: Branch from earlier message by trimming nodes (message types only, skips tool nodes)
- `save_to_file()` / `load_from_file()`: Atomic JSON persistence via temp file swap

### The Agent Input Function (`agent_input_queue.py`)
Implements async request-response pattern for agent input requests, enabling agents to request human feedback mid-conversation.

Flow:
1. Agent calls `get_input()` which creates an asyncio.Future and sends AgentInputRequest to frontend
2. User responds in frontend, sends HumanInputResponse
3. `provide_input()` resolves the Future, unblocking the agent
4. Supports cancellation via CancellationToken on interrupt


## WebSocket Protocol

### Incoming (Client to Server)
- `COMPONENT_GENERATION_REQUEST`: Pre-run AI component generation
- `RUN_START_CONFIRMED`: Start with approved analysis components
- `USER_INTERRUPT`: Pause conversation for user input
- `HUMAN_INPUT_RESPONSE`: Response to agent input request
- `USER_DIRECTED_MESSAGE`: Message to specific agent with tree branching
- `TERMINATE_REQUEST`: Graceful run termination

### Outgoing (Server to Client)
- `AGENT_MESSAGE`: Agent response with AI-generated summary
- `TREE_UPDATE`: Full conversation tree structure
- `TOOL_CALL` / `TOOL_EXECUTION`: Tool request and results
- `STATE_UPDATE`: Current manager state (state_of_run, tool_call_facts, handoff_context)
- `ANALYSIS_UPDATE`: Watchlist component scores
- `AGENT_INPUT_REQUEST`: Request for user feedback
- `STREAM_END` / `RUN_TERMINATION`: Conversation completion
