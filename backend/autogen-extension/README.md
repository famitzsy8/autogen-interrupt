# AutoGen Extension

This directory contains the modified AutoGen AgentChat 0.7.4 framework with thesis-specific extensions for human-in-the-loop multi-agent conversations. The modifications enable interrupt handling, conversation branching, plugin-based state management, and feedback components to enable a user-defined feedback system in the agent team.

We list each functionality and its implementation in the following sections.

## Interrupt Handling

Interrupt handling was done by adding a new `interrupt()` method in the `BaseGroupChat` class and added a new `UserInterrupt` event, such that the `BaseGroupChatManager` can handle the interrupt, and a new `UserDirectedMessage` event, such that the manager can handle the user directed message.

We additionally added a `GroupChatBranch` event, that synchronizes the agent buffers with each other, when the conversation branches.

The translation middleware outlined in Section 5.4.3 is implemented in the `teams/_group_chat/_agent_buffer_node_mapping.py` and `teams/_group_chat/_node_message_mapping.py` files. According logic to make the agents themselves handle the branch was is in place in the `ChatAgentContainer` class.


## Plugin System

The plugin system provides extensibility without modifying core manager code. The protocol in `teams/_group_chat/plugins/_base.py` defines lifecycle hooks that plugins implement:

- `on_message_added(message, thread, token)`: Called after each message is added to the thread
- `on_before_speaker_selection(thread, candidates, all_participants)`: Can return a speaker override before AI selection
- `on_user_message(message, is_directed, target, token)`: Process user input for state updates
- `on_branch(trim_count, new_thread_length)`: Recover state after conversation branching
- `get_state_for_agent()` / `get_state_for_selector()`: Inject state into prompts
- `save_state()` / `load_state()`: Persist plugin state across sessions

Plugins are registered via `register_plugin()` on the manager and stored in `_plugins: list[GroupChatPlugin]`. The `SelectorGroupChatManager` calls these hooks at appropriate points in the conversation flow, and plugin states are saved/loaded alongside manager state.

Two plugins are implemented: `StateContextPlugin` for cognitive offloading (above) and `AnalysisWatchlistPlugin` for quality assurance scoring against user-defined criteria.

## State Management

State management adds a `StateUpdateEvent` in `teams/_group_chat/_events.py` that plugins can emit to broadcast state snapshots. This event carries `state_of_run`, `tool_call_facts`, and `handoff_context` fields, allowing the frontend to display current conversation state.

