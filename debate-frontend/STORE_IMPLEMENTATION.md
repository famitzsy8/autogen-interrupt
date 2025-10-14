# Debate Frontend - Zustand Store Implementation

## Overview

This document describes the Zustand store implementation for the debate frontend application. The store manages WebSocket connections, conversation state, and user interactions following the specifications in `parallel-plan.md`.

## Files Created

### Core Files

1. **`src/types/index.ts`** (170 lines)
   - TypeScript types matching backend Pydantic models
   - Enums for connection state, stream state, and agent names
   - Interfaces for all WebSocket messages
   - Full type safety across the application

2. **`src/store/debateStore.ts`** (471 lines)
   - Main Zustand store with complete state management
   - WebSocket connection handling with auto-reconnect
   - Message handling for all server message types
   - Actions for user interactions
   - Includes devtools middleware for debugging

3. **`src/hooks/useDebateStore.ts`** (195 lines)
   - Typed hooks for accessing store state and actions
   - Prevents unnecessary re-renders by selecting minimal state
   - Convenience hooks for common use cases
   - Best practice patterns for React components

4. **`src/constants/agents.ts`** (95 lines)
   - Agent configuration with colors and display names
   - Helper functions for accessing agent metadata
   - Matches debate team configuration from backend

### Supporting Files

5. **`src/components/DebateConnection.tsx`**
   - Example component showing store usage
   - Demonstrates connection management
   - Shows error handling patterns

6. **`src/store/README.md`**
   - Comprehensive documentation
   - Usage examples
   - Best practices
   - Integration guide

## State Management

### WebSocket Connection State

```typescript
{
  connectionState: 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error',
  wsConnection: {
    ws: WebSocket | null,
    reconnectAttempts: number,
    reconnectTimeout: ReturnType<typeof setTimeout> | null
  }
}
```

### Conversation State

```typescript
{
  messages: AgentMessage[],              // All agent messages
  conversationTree: TreeNode | null,     // Full tree structure
  currentBranchId: string,               // Active branch ID
  activeNodeId: string | null            // Current node ID
}
```

### Stream State

```typescript
{
  streamState: 'idle' | 'streaming' | 'interrupted' | 'ended',
  isInterrupted: boolean
}
```

### User Interaction State

```typescript
{
  selectedAgent: string | null,          // Target agent for messages
  trimCount: number,                     // Nodes to trim for branching
  userMessageDraft: string               // Draft message content
}
```

### Error State

```typescript
{
  error: {
    code: string,
    message: string,
    timestamp: string
  } | null
}
```

## Key Features

### 1. WebSocket Management

- **Auto-connect on mount** - Connects when component initializes
- **Auto-reconnect** - Exponential backoff (max 5 attempts)
- **Connection states** - Tracks disconnected/connecting/connected/reconnecting/error
- **Clean disconnect** - Properly closes connections on unmount

### 2. Message Handling

- **Type-safe parsing** - All messages validated against TypeScript types
- **Automatic routing** - Routes messages to appropriate handlers
- **Tree synchronization** - Updates tree structure from server
- **Error recovery** - Handles parsing errors gracefully

### 3. User Interactions

- **Send user messages** - With target agent and trim count
- **Send interrupts** - Pause agent conversation stream
- **Draft management** - Track user message drafts
- **Agent selection** - Select target agent for messages

### 4. Type Safety

- **No `any` types** - Strict TypeScript throughout
- **Backend model matching** - Types mirror Pydantic models
- **Exhaustive checks** - All message types handled
- **Compile-time safety** - Catches errors before runtime

### 5. Error Handling

- **Connection errors** - WebSocket failures tracked
- **Message parsing errors** - Invalid JSON handling
- **Validation errors** - Empty messages rejected
- **User-friendly errors** - Error codes and messages

## Usage Patterns

### Basic Component Example

```typescript
import {
  useMessages,
  useIsStreaming,
  useMessageActions,
} from '../hooks/useDebateStore'

function ChatDisplay() {
  const messages = useMessages()
  const isStreaming = useIsStreaming()
  const { sendInterrupt } = useMessageActions()

  return (
    <div>
      {messages.map((msg) => (
        <div key={msg.node_id}>
          <strong>{msg.agent_name}:</strong> {msg.content}
        </div>
      ))}
      {isStreaming && (
        <button onClick={sendInterrupt}>Interrupt</button>
      )}
    </div>
  )
}
```

### Sending User Messages

```typescript
import {
  useUserMessageDraft,
  useSelectedAgent,
  useTrimCount,
  useMessageActions,
  useUserInteractionActions,
} from '../hooks/useDebateStore'

function UserInput() {
  const draft = useUserMessageDraft()
  const selectedAgent = useSelectedAgent()
  const trimCount = useTrimCount()
  const { sendUserMessage } = useMessageActions()
  const { setUserMessageDraft, setSelectedAgent } = useUserInteractionActions()

  const handleSend = () => {
    if (draft && selectedAgent) {
      sendUserMessage(draft, selectedAgent, trimCount)
    }
  }

  return (
    <div>
      <textarea
        value={draft}
        onChange={(e) => setUserMessageDraft(e.target.value)}
      />
      <select
        value={selectedAgent || ''}
        onChange={(e) => setSelectedAgent(e.target.value)}
      >
        <option value="">Select agent...</option>
        {/* Agent options */}
      </select>
      <button onClick={handleSend}>Send</button>
    </div>
  )
}
```

## Integration with Backend

### WebSocket URL

Default: `ws://localhost:8000/ws/debate`
Configure via: `VITE_WS_URL` environment variable

### Message Types

Client → Server:
- `user_interrupt` - Pause agent stream
- `user_directed_message` - Send message to agent

Server → Client:
- `agent_message` - Agent sent a message
- `interrupt_acknowledged` - Interrupt successful
- `stream_end` - Conversation ended
- `error` - Error occurred
- `tree_update` - Tree structure updated

### Type Matching

All types in `src/types/index.ts` match the Pydantic models in `debate-backend/models.py`:

- `AgentMessage` ↔ `AgentMessage`
- `UserInterrupt` ↔ `UserInterrupt`
- `UserDirectedMessage` ↔ `UserDirectedMessage`
- `TreeNode` ↔ `TreeNode`
- `TreeUpdate` ↔ `TreeUpdate`

## Agent Configuration

Five debate agents configured with colors:

1. **Jara_Supporter** - Red `rgba(239, 68, 68, 0.4)`
2. **Kast_Supporter** - Blue `rgba(59, 130, 246, 0.4)`
3. **Neural_Agent** - Purple `rgba(168, 85, 247, 0.4)`
4. **Moderate_Left** - Light Blue `rgba(125, 211, 252, 0.4)`
5. **Moderate_Right** - Orange `rgba(251, 146, 60, 0.4)`

Plus system agents:
- **User** - White `rgba(255, 255, 255, 0.4)`
- **System** - Gray `rgba(156, 163, 175, 0.4)`

## Testing

### Build Verification

```bash
cd debate-frontend
npm run build
```

Build successful with no TypeScript errors.

### Store Reset

```typescript
import { useDebateStore } from './store/debateStore'

// Reset store in tests
beforeEach(() => {
  useDebateStore.getState().reset()
})
```

## Next Steps

1. **Create UI components** - Build chat display and tree visualization
2. **Integrate store** - Connect components to store hooks
3. **Test WebSocket flow** - Verify end-to-end message handling
4. **Add optimistic updates** - Update UI before server confirmation
5. **Implement persistence** - Save conversation history to localStorage

## Performance Considerations

- **Selective re-renders** - Use specific hooks instead of full state
- **Message batching** - Consider batching for high-frequency messages
- **Tree memoization** - Memoize tree transformations
- **WebSocket efficiency** - Reuse single connection across app

## Security Considerations

- **Input validation** - All user messages validated before sending
- **Error sanitization** - Error messages don't leak sensitive data
- **Connection cleanup** - WebSocket properly closed on unmount
- **Type safety** - Prevents injection via TypeScript checks

## Monitoring

With Zustand DevTools, you can:

1. **Inspect state** - View current store state
2. **Track actions** - See all dispatched actions
3. **Time travel** - Revert to previous states
4. **Export state** - Save state snapshots for debugging

## Summary

The Zustand store implementation provides:

- ✅ **Complete type safety** - No `any` types, matches backend models
- ✅ **WebSocket management** - Auto-connect, reconnect, error handling
- ✅ **Conversation state** - Messages, tree, branches
- ✅ **User interactions** - Send messages, interrupts, branching
- ✅ **Error handling** - Comprehensive error tracking
- ✅ **Typed hooks** - Easy React integration
- ✅ **Agent configuration** - Colors and metadata
- ✅ **Documentation** - Complete usage guide
- ✅ **Build verified** - TypeScript compilation successful

Total: **931 lines** of production-quality, type-safe code.
