# Debate Store Architecture

This directory contains the Zustand store for managing the debate frontend application state.

## Overview

The debate store manages all application state including WebSocket connections, conversation messages, conversation tree data, interrupt state, and user interactions.

## Files

### `debateStore.ts`
Main Zustand store with all state and actions. Uses the `devtools` middleware for debugging in development.

### Key State Managed

1. **WebSocket Connection State**
   - Connection status (disconnected/connecting/connected/reconnecting/error)
   - WebSocket instance
   - Reconnection attempts and timeout management

2. **Conversation Data**
   - Array of all agent messages
   - Complete conversation tree structure
   - Current branch ID
   - Active node ID

3. **Stream State**
   - Current stream status (idle/streaming/interrupted/ended)
   - Interrupt flag

4. **User Interaction State**
   - Selected agent for user messages
   - Trim count for branching
   - User message draft

5. **Error State**
   - Current error information (if any)

## Usage Examples

### Basic Usage

```typescript
import { useDebateStore } from './store/debateStore'

function MyComponent() {
  const messages = useDebateStore((state) => state.messages)
  const connect = useDebateStore((state) => state.connect)

  return (
    // component JSX
  )
}
```

### Using Typed Hooks (Recommended)

```typescript
import {
  useMessages,
  useConnectionActions,
  useMessageActions,
} from '../hooks/useDebateStore'

function MyComponent() {
  const messages = useMessages()
  const { connect } = useConnectionActions()
  const { sendUserMessage } = useMessageActions()

  // Use the state and actions
}
```

## Store Actions

### WebSocket Management

- **`connect(url: string)`** - Connect to WebSocket server
- **`disconnect()`** - Disconnect from WebSocket server
- **`reconnect()`** - Attempt to reconnect with exponential backoff

### Message Handling

- **`handleServerMessage(message: ServerMessage)`** - Process incoming server messages
- **`addMessage(message: AgentMessage)`** - Add new agent message to the array
- **`updateConversationTree(treeUpdate: TreeUpdate)`** - Update the tree structure

### User Interactions

- **`sendUserMessage(content, targetAgent, trimCount)`** - Send a user message to a specific agent
- **`sendInterrupt()`** - Send an interrupt request to pause the agent stream
- **`setSelectedAgent(agentName)`** - Set the target agent for user messages
- **`setTrimCount(count)`** - Set the trim count for branching
- **`setUserMessageDraft(draft)`** - Update the user message draft

### State Management

- **`setStreamState(state)`** - Update the stream state
- **`setInterrupted(interrupted)`** - Set the interrupted flag
- **`setError(error)`** - Set an error
- **`clearError()`** - Clear the current error
- **`reset()`** - Reset the store to initial state

## Reconnection Strategy

The store implements automatic reconnection with exponential backoff:

- Maximum 5 reconnection attempts
- Base delay of 1000ms
- Delay doubles with each attempt (1s, 2s, 4s, 8s, 16s)
- Stops attempting after max attempts reached

## Type Safety

All store state and actions are fully typed with TypeScript. The store uses types from `../types/index.ts` that mirror the backend Pydantic models to ensure type safety across the WebSocket communication layer.

## Error Handling

The store includes comprehensive error handling:

- WebSocket connection errors
- Message parsing errors
- Validation errors for user actions
- All errors are stored in the `error` state with code, message, and timestamp

## Best Practices

1. **Use typed hooks** from `../hooks/useDebateStore.ts` instead of accessing the store directly
2. **Select minimal state** to avoid unnecessary re-renders
3. **Don't mutate state** - all updates go through store actions
4. **Handle errors** - check the error state and clear when appropriate
5. **Clean up** - call `disconnect()` when unmounting components that manage the connection

## Development Tools

The store is wrapped with Zustand's `devtools` middleware. You can use the Redux DevTools browser extension to:

- Inspect current state
- View action history
- Time-travel debug
- Export/import state snapshots

## Testing

When testing components that use the store:

```typescript
import { useDebateStore } from './store/debateStore'

// Reset store before each test
beforeEach(() => {
  useDebateStore.getState().reset()
})

// Access store state in tests
const state = useDebateStore.getState()
const { messages, connect } = state
```

## WebSocket Message Flow

1. **Client connects** → `connect(url)` → WebSocket opened → `connectionState` = 'connected'
2. **Server sends message** → `ws.onmessage` → `handleServerMessage()` → State updated
3. **User interrupts** → `sendInterrupt()` → Server processes → `interrupt_acknowledged` received
4. **User sends message** → `sendUserMessage()` → Server processes → New messages received
5. **Connection lost** → `ws.onclose` → `reconnect()` → Exponential backoff retry

## Integration with Backend

The store types match the backend Pydantic models in `/debate-backend/models.py`:

- `AgentMessage` → Backend's `AgentMessage`
- `UserInterrupt` → Backend's `UserInterrupt`
- `UserDirectedMessage` → Backend's `UserDirectedMessage`
- `TreeNode` → Backend's `TreeNode`
- `TreeUpdate` → Backend's `TreeUpdate`

All timestamps use ISO 8601 format for consistency with the backend.
