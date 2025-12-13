# Plugins

This directory contains the plugin system for extending group chat behavior. Plugins receive lifecycle hooks from the manager and can inject state, override speaker selection, and persist their own state.


## Plugin Protocol (`_base.py`)

The `GroupChatPlugin` protocol defines the contract for all plugins:

- `on_message_added(message, thread, token)`: Called after each message is added
- `on_before_speaker_selection(thread, candidates, all_participants)`: Can return speaker override
- `on_user_message(message, is_directed, target, token)`: Process user input
- `on_branch(trim_count, new_thread_length)`: Recover state after conversation branching
- `get_state_for_agent()`: Return template variables for agent prompts
- `get_state_for_selector()`: Return template variables for selector prompt
- `save_state()` / `load_state()`: Persist plugin state across sessions


## State Context Plugin (`state_context/`)

Implements cognitive offloading via three-state context management.

### Three-State Model
- `state_of_run`: Current research progress and next steps (updated after agent messages)
- `tool_call_facts`: Verified facts whiteboard from tool executions (append-only)
- `handoff_context`: Agent selection rules and user preferences

### Key Files
- `_plugin.py`: Main plugin class with lifecycle hooks and LLM-based state updates
- `_prompts.py`: Prompts for updating each state component
- `_models.py`: StateSnapshot and related data structures
- `_handoff_intent_router.py`: Two-pass intent detection (regex then LLM) for handoff changes

### State Recovery
Caches snapshots at each message index in `_state_snapshots: dict[int, StateSnapshot]`. On branch, recovers the nearest snapshot at or before the trim point.


## Analysis Watchlist Plugin (`analysis_watchlist/`)

Provides hallucination detection and user feedback triggers via quality assurance scoring.

### Scoring Flow
1. User defines 2-5 analysis criteria (what to watch for)
2. LLM parses description into `AnalysisComponent` objects
3. Each agent message scored against components (1-10 scale)
4. When score >= threshold, triggers user feedback by forcing user_proxy selection

### Key Files
- `_plugin.py`: Main plugin class tracking pending analysis and emitting AnalysisUpdate events
- `_service.py`: LLM-based parsing and scoring service
- `_prompts.py`: Prompts for component parsing and message scoring
- `_models.py`: AnalysisComponent, ComponentScore, AnalysisUpdate definitions

