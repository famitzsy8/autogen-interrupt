## Autogen delta log (v0.7.4) — changes applied in this workspace

Context
- Python: 3.13.7 (darwin arm64)
- Pinned deps for OpenAI client compatibility: httpx==0.27.2, httpcore==1.0.5, openai==1.51.0, tiktoken (latest).
- All code changes below were made directly under site-packages for `autogen_agentchat` 0.7.4.

---

1) File: autogen_agentchat/messages.py
- Added:
  - `class UserTextMessage(BaseTextChatMessage)` with `type="UserTextMessage"`.
  - Registration of `UserTextMessage` in `MessageFactory`.
  - Inclusion of `UserTextMessage` in `ChatMessage` union and `__all__`.

Impact
- Provides a first-class chat message type for user-injected control messages.

---

2) File: autogen_agentchat/teams/_group_chat/_events.py
- Added:
  - `class UserInterrupt(BaseModel)`: empty payload control event.
  - `class UserDirectedMessage(BaseModel)`: fields `target: str`, `message: SerializeAsAny[BaseChatMessage]`.

Impact
- Introduces control signals to pause conversations and inject a user message to a specific participant.

---

3) File: autogen_agentchat/teams/_group_chat/_base_group_chat_manager.py
- Imports:
  - Added `TextMessage` for DEBUG markers.
- Initialization:
  - Extended `sequential_message_types` to include `UserInterrupt` and `UserDirectedMessage`.
- Handlers added:
  - `@rpc async def handle_user_interrupt(...)`: publishes a DEBUG line, then signals termination via `_signal_termination(StopMessage("USER_INTERRUPT"))` without clearing thread.
  - `@rpc async def handle_user_directed_message(...)`: publishes a DEBUG line; logs the user message to the output topic; enqueues it to the output queue; relays it to the group topic (so `ChatAgentContainer`s buffer it); appends to `_message_thread`; applies termination; finally sends `GroupChatRequestPublish` only to the targeted participant and updates `_active_speakers`.
- Correctness fix:
  - Ensured `handle_start` is decorated with `@rpc` so `GroupChatStart` is handled (preventing "Unhandled message ... GroupChatStart").

Impact
- Enables pause and user-directed injection flows at the manager level and prevents unhandled start events.

---

4) File: autogen_agentchat/teams/_group_chat/_base_group_chat.py
- New public APIs:
  - `async def interrupt(self) -> None`:
    - Ensures embedded runtime is started (idempotent), sends `UserInterrupt`, waits briefly (<=2s) for a `GroupChatTermination`, then attempts to stop runtime when idle and drains the queue.
  - `async def send_user_message(self, msg: TextMessage, agent_name: str) -> TaskResult`:
    - Ensures embedded runtime is started (idempotent), sends `UserDirectedMessage`, then collects output until either:
      - target agent replies (stop_reason="USER_MESSAGE_COMPLETED"), or
      - termination arrives, or
      - a timeout occurs (stop_reason="USER_MESSAGE_TIMEOUT").
    - Attempts to stop runtime when idle and drains the queue.
- Small behavior adjustments:
  - Ignore `RuntimeError("Runtime is already started")` when starting embedded runtime.

Impact
- Provides application-facing control APIs with timeouts and lifecycle hygiene to avoid hangs.

---

5) File: autogen_agentchat/agents/_user_control_agent.py (new)
- Added `class UserControlAgent(BaseChatAgent)`:
  - Thin helper exposing `interrupt(team)` and `send(team, msg, agent)` that call the team APIs.
  - Minimal `on_messages`/`on_messages_stream` returning empty `TextMessage` to satisfy base class.

Impact
- Gives a programmatic agent facade for proactive user control.

---

6) File: autogen_agentchat/agents/__init__.py
- Exported `UserControlAgent` in imports and `__all__`.

Impact
- Makes `UserControlAgent` discoverable to consumers via `from autogen_agentchat.agents import UserControlAgent`.

---

7) Tests added in repo (workspace, not site-packages)
- tests/test_interrupt_dummy.py
  - Dummy agents (no model calls). Runs a short stream, interrupts, then sends a user-directed message. Prints the stream, e.g.:
    - `DEBUG: handle_user_directed_message target=Bob`, `user Hello`, `Bob ACK-X`.
  - Confirms `stop_reason: USER_MESSAGE_COMPLETED`.
- tests/test_openai_client_construct.py
  - Verifies `OpenAIChatCompletionClient` constructs with pinned dependencies (no network).

Impact
- Reusable validation for the new control flows and environment setup.

---

Known deviations / considerations
- Group chat manager now emits ad hoc DEBUG `TextMessage`s to the output topic; these should be gated behind a debug flag or converted into structured events.
- `handle_user_directed_message` broadcasts a `GroupChatStart` to output/group topics to mimic start ingestion; upstream might prefer a dedicated ingestion utility to avoid duplication.
- Team-level APIs include timeouts and runtime lifecycle management; upstream may want these as optional parameters or utilities to keep the base class minimal.

Rollback note
- To revert, reinstall `autogen-agentchat==0.7.4` into the venv or replace the modified files with the originals from the wheel.


