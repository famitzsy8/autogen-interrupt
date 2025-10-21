# Quick Start Guide - Debate Store

## Installation Complete ✓

The Zustand store is fully implemented and ready to use.

## File Structure

```
src/
├── types/
│   └── index.ts              # TypeScript types (170 lines)
├── store/
│   ├── debateStore.ts        # Zustand store (471 lines)
│   └── README.md             # Store documentation
├── hooks/
│   └── useDebateStore.ts     # Typed hooks (195 lines)
├── constants/
│   └── agents.ts             # Agent configs (95 lines)
└── components/
    └── DebateConnection.tsx  # Example component
```

## Import What You Need

```typescript
// Types
import { AgentMessage, TreeNode, ConnectionState } from './types'

// Store (direct access)
import { useDebateStore } from './store/debateStore'

// Hooks (recommended)
import {
  useMessages,
  useConversationTree,
  useConnectionActions,
  useMessageActions,
} from './hooks/useDebateStore'

// Agent configs
import { AGENT_CONFIGS, getAgentColor } from './constants/agents'
```

## Common Patterns

### 1. Connect to WebSocket

```typescript
import { useEffect } from 'react'
import { useConnectionActions } from './hooks/useDebateStore'

function App() {
  const { connect, disconnect } = useConnectionActions()

  useEffect(() => {
    connect('ws://localhost:8000/ws/debate')
    return () => disconnect()
  }, [])
}
```

### 2. Display Messages

```typescript
import { useMessages } from './hooks/useDebateStore'
import { getAgentColor } from './constants/agents'

function ChatDisplay() {
  const messages = useMessages()

  return (
    <div>
      {messages.map((msg) => (
        <div
          key={msg.node_id}
          style={{ borderLeft: `4px solid ${getAgentColor(msg.agent_name)}` }}
        >
          <strong>{msg.agent_name}:</strong> {msg.content}
        </div>
      ))}
    </div>
  )
}
```

### 3. Send User Message

```typescript
import { useMessageActions } from './hooks/useDebateStore'

function UserInput() {
  const { sendUserMessage } = useMessageActions()

  const handleSend = () => {
    sendUserMessage(
      'My message content',
      'Jara_Supporter',  // target agent
      0                  // trim_count (0 = no branching)
    )
  }
}
```

### 4. Interrupt Stream

```typescript
import { useIsStreaming, useMessageActions } from './hooks/useDebateStore'

function InterruptButton() {
  const isStreaming = useIsStreaming()
  const { sendInterrupt } = useMessageActions()

  if (!isStreaming) return null

  return <button onClick={sendInterrupt}>Interrupt</button>
}
```

### 5. Handle Errors

```typescript
import { useError, useErrorActions } from './hooks/useDebateStore'

function ErrorDisplay() {
  const error = useError()
  const { clearError } = useErrorActions()

  if (!error) return null

  return (
    <div className="error">
      {error.code}: {error.message}
      <button onClick={clearError}>Dismiss</button>
    </div>
  )
}
```

## Agent Names

Use the enum for type safety:

```typescript
import { AgentName } from './types'

AgentName.JARA_SUPPORTER    // 'Jara_Supporter'
AgentName.KAST_SUPPORTER    // 'Kast_Supporter'
AgentName.NEURAL_AGENT      // 'Neural_Agent'
AgentName.MODERATE_LEFT     // 'Moderate_Left'
AgentName.MODERATE_RIGHT    // 'Moderate_Right'
AgentName.USER              // 'User'
AgentName.SYSTEM            // 'System'
```

## Connection States

```typescript
import { ConnectionState } from './types'

ConnectionState.DISCONNECTED   // 'disconnected'
ConnectionState.CONNECTING     // 'connecting'
ConnectionState.CONNECTED      // 'connected'
ConnectionState.RECONNECTING   // 'reconnecting'
ConnectionState.ERROR          // 'error'
```

## Stream States

```typescript
import { StreamState } from './types'

StreamState.IDLE         // 'idle'
StreamState.STREAMING    // 'streaming'
StreamState.INTERRUPTED  // 'interrupted'
StreamState.ENDED        // 'ended'
```

## Debugging

Install Redux DevTools extension, then:

1. Open DevTools
2. Go to Redux tab
3. View actions and state changes
4. Time-travel through state

## Environment Variables

Create `.env` file:

```bash
VITE_WS_URL=ws://localhost:8000/ws/debate
```

## Build & Run

```bash
# Install dependencies
npm install

# Development
npm run dev

# Production build
npm run build

# Preview production
npm run preview
```

## TypeScript

All code is fully typed with strict mode enabled:

- ✓ No `any` types
- ✓ Strict null checks
- ✓ All parameters typed
- ✓ Exhaustive checks
- ✓ Type inference

## Next Steps

1. Build UI components using the store
2. Connect to backend WebSocket
3. Test full message flow
4. Implement tree visualization
5. Add user controls

## Need Help?

- Check `src/store/README.md` for detailed documentation
- Review `STORE_IMPLEMENTATION.md` for architecture overview
- Examine `src/components/DebateConnection.tsx` for working example

## Key Points

1. **Use hooks, not direct store access** - Better performance
2. **Handle errors** - Always check error state
3. **Clean up connections** - Disconnect on unmount
4. **Type everything** - No `any` types allowed
5. **Follow React patterns** - Use hooks in function components

Happy coding! 🚀
