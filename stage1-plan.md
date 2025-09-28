## Autogen Interrupt: Stage 1 Plan

### Goal
Design and integrate a `UserControlAgent` and two signals — **USER_INTERRUPT** and **USER_MESSAGE** — into Autogen AgentChat (v0.7.4) so a human can proactively pause/suspend an in-flight team conversation and later inject a directed message to a specific agent while preserving team state and message history.

### High-level Approach
- Introduce two new message/event types and a small orchestration layer that cleanly fits into Autogen’s team runtime:
  - A termination-like, resumable pause signal handled at the team/manager level (without tearing down the runtime): USER_INTERRUPT.
  - A post-interrupt user-directed message to a specific participant: USER_MESSAGE(MSG, AGENT).
- Extend the existing group chat manager base to support pause/resume semantics and injection of a user-targeted message to a chosen participant after an interrupt.
- Add a new `UserControlAgent` that can publish these signals to the team and optionally persist/restore state to support pick-up later.

---

### New/Updated Objects

- New message/event types in `autogen_agentchat.teams._group_chat._events`:
  - `UserInterrupt`: team-level request to suspend activity, persist state, and emit a termination-like end-of-stream sentinel to the caller without error.
  - `UserDirectedMessage`: carries a user message payload and the intended target participant name.

- New chat message in `autogen_agentchat.messages`:
  - `UserTextMessage(BaseTextChatMessage)`: a typed wrapper for user-injected text, used by `UserDirectedMessage` and output streams for UI rendering.

- New agent in `autogen_agentchat.agents`:
  - `UserControlAgent(BaseChatAgent)`: publishes `UserInterrupt` and `UserDirectedMessage` to the group chat. Unlike `UserProxyAgent`, it does not solicit input; it emits explicit control signals programmatically/UI-driven.

- Extensions to existing classes:
  - `BaseGroupChatManager(SequentialRoutedAgent)` (in `_base_group_chat_manager.py`):
    - Handle `UserInterrupt` as an RPC that:
      - freezes turn progression (no more `GroupChatRequestPublish`),
      - puts a `GroupChatTermination(StopMessage("USER_INTERRUPT"))` on the output queue,
      - resets only transient counters but preserves `_message_thread` for continuity.
    - Handle `UserDirectedMessage` as an RPC that:
      - appends the provided `UserTextMessage` to `_message_thread`,
      - validates the target agent name and publishes a `GroupChatRequestPublish` only to that participant,
      - resumes normal selection logic after the targeted response is received.

  - `BaseGroupChat(Team)` (in `_base_group_chat.py`):
    - Public methods bridging to the manager:
      - `interrupt()` → sends `UserInterrupt` to the manager topic and drains to a termination sentinel (like a soft stop). Team remains reusable; `save_state()` can be called right after.
      - `send_user_message(msg: TextMessage, agent_name: str)` → sends `UserDirectedMessage` to the manager; returns only when the targeted participant’s response arrives or termination kicks in.

  - Optional: extend `TeamState`/manager states to include an `interrupted: bool` flag to indicate the last stop reason was a user interrupt, aiding UX flows.

---

### Ontology of Signals

- USER_INTERRUPT
  - Type: team-level control event.
  - Producer: `UserControlAgent` or host application via team API.
  - Consumer: `BaseGroupChatManager.handle_user_interrupt` (RPC).
  - Semantics: graceful, resumable pause — emit `GroupChatTermination(StopMessage("USER_INTERRUPT"))` so the stream ends, but keep manager/participants registered and the message thread in memory.

- USER_MESSAGE(MSG, AGENT)
  - Type: team-level control event carrying a `UserTextMessage` and a target participant name.
  - Producer: `UserControlAgent` or host application via team API after an interrupt.
  - Consumer: `BaseGroupChatManager.handle_user_directed_message` (RPC) → routes only to the selected participant via `GroupChatRequestPublish` and appends to `_message_thread`.
  - Semantics: single-turn injection that restarts the team flow from the preserved history.

---

### Where Signals Arise and Are Handled

- Arise from:
  - Methods on `UserControlAgent` (e.g., `interrupt(team)`, `send(team, msg, agent)`), or
  - Team convenience methods (`BaseGroupChat.interrupt`, `BaseGroupChat.send_user_message`).

- Handled in:
  - `BaseGroupChatManager` via `@rpc` handlers:
    - `handle_user_interrupt(UserInterrupt, ctx)`
    - `handle_user_directed_message(UserDirectedMessage, ctx)`
  - The manager updates `_message_thread`, coordinates targeted publish to the chosen participant, and manages `_active_speakers` so selection continues after the targeted agent responds.

---

### Concrete Edit Points (Functions to Add/Override)

- File: `autogen_agentchat/teams/_group_chat/_events.py`
  - Add:
    - `class UserInterrupt(BaseModel): ...`
    - `class UserDirectedMessage(BaseModel): message: SerializeAsAny[UserTextMessage]; target: str`

- File: `autogen_agentchat/messages.py`
  - Add:
    - `class UserTextMessage(BaseTextChatMessage): type: Literal["UserTextMessage"] = "UserTextMessage"`
    - Register `UserTextMessage` in `MessageFactory` and `ChatMessage` union.

- File: `autogen_agentchat/teams/_group_chat/_base_group_chat_manager.py`
  - Constructor: include `UserInterrupt` and `UserDirectedMessage` in `sequential_message_types`.
  - Add RPC handlers:
    - `@rpc async def handle_user_interrupt(self, message: UserInterrupt, ctx: MessageContext) -> None:`
      - put `GroupChatTermination(StopMessage("USER_INTERRUPT", source=self._name))` into output queue via `_signal_termination`.
      - do not clear `_message_thread`; optionally set an internal `_interrupted = True` flag.
    - `@rpc async def handle_user_directed_message(self, message: UserDirectedMessage, ctx: MessageContext) -> None:`
      - validate `message.target in self._participant_names`.
      - append `message.message` to `_message_thread`.
      - publish `GroupChatRequestPublish()` only to the target participant’s topic.
      - set `_active_speakers = [message.target]` so the manager awaits the response before selecting next speakers.

- File: `autogen_agentchat/teams/_group_chat/_base_group_chat.py`
  - Add public APIs:
    - `async def interrupt(self) -> None:`
      - send `UserInterrupt` to manager; consume stream until a `GroupChatTermination` is observed.
    - `async def send_user_message(self, msg: TextMessage | UserTextMessage, agent_name: str) -> TaskResult:`
      - send `UserDirectedMessage` to manager; then follow the normal output stream until `TaskResult` or termination.

- File: `autogen_agentchat/agents/_user_control_agent.py` (new)
  - `class UserControlAgent(BaseChatAgent)` implementing:
    - `produced_message_types = (TextMessage,)` (for completeness; agent mainly emits control RPCs via team APIs rather than returning chat text.)
    - Helper methods that call the team methods:
      - `async def interrupt(self, team: BaseGroupChat) -> None`
      - `async def send(self, team: BaseGroupChat, msg: str, agent: str) -> TaskResult`

- Optional: `state/_states.py`
  - Extend manager state with `interrupted: bool = False` and persist/restore in manager implementations.

---

### Delegation Handling Fit
- Existing delegation path stays intact:
  - `BaseGroupChatManager` selects speakers and emits `GroupChatRequestPublish` → `ChatAgentContainer` buffers and calls each participant agent’s `on_messages_stream` → returns `GroupChatAgentResponse`/`GroupChatTeamResponse` → manager updates thread and continues.
- Our additions only interpose at manager level to:
  - short-circuit with an interrupt termination event, or
  - inject a user message and route it to a single participant before resuming normal selection.

---

### Tool Call Handling Fit
- Tool execution remains within `AssistantAgent` and `autogen_core.tools` workbenches.
- No changes required to tool APIs. The interruption simply ends the current stream early; subsequent `send_user_message` restarts with preserved `_message_thread` so tool context continuity is maintained.

---

### Message History Handling
- Message thread is the authoritative history at team level: `BaseGroupChatManager._message_thread`.
- On interrupt, we do not clear `_message_thread`; we emit a termination event and keep state in memory. Optionally, callers can `await team.save_state()` immediately after to persist via `TeamState` and manager state.
- On user-directed message, we append `UserTextMessage(source="user", content=...)` before routing to the target participant, so history reflects the human input.

---

### Detailed Steps to Implement

1) Add new message/event types:
   - Implement `UserTextMessage` and register it in `MessageFactory` and unions.
   - Implement `UserInterrupt` and `UserDirectedMessage` events.

2) Extend `BaseGroupChatManager`:
   - Include new types in sequential handling.
   - Implement `handle_user_interrupt` and `handle_user_directed_message` per above.
   - Ensure `_active_speakers` logic tolerates a forced single-speaker continuation after `UserDirectedMessage`.

3) Add convenience APIs on `BaseGroupChat`:
   - `interrupt()` and `send_user_message()` wrappers that send RPCs to the manager topic using `AgentRuntime.send_message(...)`.

4) Create `UserControlAgent`:
   - Thin wrapper that invokes the team methods from UI or application code.

5) Persistence & resume:
   - Optionally add `interrupted: bool` to manager state and wire into `save_state/load_state` for UX.
   - Document recommended flow: run → interrupt → save_state → later load_state → send_user_message → continue.

6) Tests/Examples:
   - Example notebook/script: start `Swarm` with two `AssistantAgent`s; interrupt mid-flow; then send a directed message to one agent; verify continuation and eventual termination by existing conditions (e.g., `MaxMessageTermination`).

---

### Notes on Backward Compatibility and Minimal Invasiveness
- New classes are additive; no breaking changes to existing handlers.
- `UserInterrupt` uses the existing `GroupChatTermination` channel for stream termination, with a distinct `StopMessage` content so callers can branch on stop reason.
- Teams without `UserControlAgent` remain unaffected.

---

### Example API Sketches

Additions to manager handlers (signatures only, too long bodies omitted):
```python
@rpc
async def handle_user_interrupt(self, message: UserInterrupt, ctx: MessageContext) -> None: ...

@rpc
async def handle_user_directed_message(self, message: UserDirectedMessage, ctx: MessageContext) -> None: ...
```

Team convenience methods:
```python
async def interrupt(self) -> None: ...

async def send_user_message(self, msg: TextMessage | UserTextMessage, agent_name: str) -> TaskResult: ...
```

User control agent usage:
```python
uca = UserControlAgent("user_control")
await uca.interrupt(team)
result = await uca.send(team, "Please elaborate on step 2", agent="Bob")
```

---

### Summary
This plan introduces two first-class control signals and a `UserControlAgent` that integrate natively with Autogen’s group chat orchestration. Interrupts gracefully end the current run but preserve team composition and history; a subsequent user-directed message targets a specific agent and resumes the conversation seamlessly using existing delegation, tool, and history mechanisms.


