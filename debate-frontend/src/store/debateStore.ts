/**
 * Zustand store for managing debate application state.
 *
 * This store manages:
 * - WebSocket connection state
 * - Conversation messages
 * - Conversation tree data
 * - Interrupt state and user interactions
 * - Trim count for branching
 */

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type {
  AgentInputRequest,
  AgentInputResponse,
  AgentMessage,
  AppError,
  ConnectionState,
  MessageType,
  ServerMessage,
  StreamState,
  TreeNode,
  TreeUpdate,
  UserDirectedMessage,
  UserInterrupt,
} from '../types'
import {
  ConnectionState as ConnectionStateEnum,
  StreamState as StreamStateEnum,
} from '../types'

/**
 * WebSocket connection manager interface.
 */
interface WebSocketConnection {
  ws: WebSocket | null
  reconnectAttempts: number
  reconnectTimeout: ReturnType<typeof setTimeout> | null
}

/**
 * Debate store state interface.
 */
interface DebateState {
  // WebSocket connection state
  connectionState: ConnectionState
  wsConnection: WebSocketConnection

  // Conversation data
  messages: AgentMessage[]
  conversationTree: TreeNode | null
  currentBranchId: string
  activeNodeId: string | null

  // Stream state
  streamState: StreamState
  isInterrupted: boolean

  // User interaction state
  selectedAgent: string | null
  trimCount: number
  userMessageDraft: string

  // Agent input request state
  agentInputRequest: AgentInputRequest | null
  agentInputDraft: string

  // Error state
  error: AppError | null

  // Actions: WebSocket management
  connect: (url: string) => void
  disconnect: () => void
  reconnect: () => void

  // Actions: Message handling
  handleServerMessage: (message: ServerMessage) => void
  addMessage: (message: AgentMessage) => void
  updateConversationTree: (treeUpdate: TreeUpdate) => void

  // Actions: User interactions
  sendUserMessage: (content: string, targetAgent: string, trimCount: number) => void
  sendInterrupt: () => void
  setSelectedAgent: (agentName: string | null) => void
  setTrimCount: (count: number) => void
  setUserMessageDraft: (draft: string) => void

  // Actions: Agent input
  sendAgentInputResponse: (requestId: string, userInput: string) => void
  setAgentInputDraft: (draft: string) => void
  clearAgentInputRequest: () => void

  // Actions: State management
  setStreamState: (state: StreamState) => void
  setInterrupted: (interrupted: boolean) => void
  setError: (error: AppError | null) => void
  clearError: () => void
  reset: () => void
}

/**
 * Initial state values.
 */
const initialState = {
  connectionState: ConnectionStateEnum.DISCONNECTED,
  wsConnection: {
    ws: null,
    reconnectAttempts: 0,
    reconnectTimeout: null,
  },
  messages: [],
  conversationTree: null,
  currentBranchId: 'main',
  activeNodeId: null,
  streamState: StreamStateEnum.IDLE,
  isInterrupted: false,
  selectedAgent: null,
  trimCount: 0,
  userMessageDraft: '',
  agentInputRequest: null,
  agentInputDraft: '',
  error: null,
}

/**
 * Maximum number of reconnection attempts.
 */
const MAX_RECONNECT_ATTEMPTS = 5

/**
 * Base reconnection delay in milliseconds.
 */
const RECONNECT_DELAY_MS = 1000

/**
 * Create the debate store with devtools for debugging.
 */
export const useDebateStore = create<DebateState>()(
  devtools(
    (set, get) => ({
      ...initialState,

      /**
       * Connect to the WebSocket server.
       */
      connect: (url: string) => {
        const { wsConnection, disconnect } = get()

        // Close existing connection if any
        if (wsConnection.ws) {
          disconnect()
        }

        set({ connectionState: ConnectionStateEnum.CONNECTING })

        try {
          const ws = new WebSocket(url)

          ws.onopen = () => {
            set({
              connectionState: ConnectionStateEnum.CONNECTED,
              wsConnection: {
                ws,
                reconnectAttempts: 0,
                reconnectTimeout: null,
              },
              error: null,
            })
          }

          ws.onmessage = (event: MessageEvent) => {
            console.log('=== Frontend received message ===', event.data)
            try {
              const message: ServerMessage = JSON.parse(event.data)
              console.log('=== Parsed message type:', message.type, '===')
              get().handleServerMessage(message)
              console.log('=== Message handled successfully ===')
            } catch (error) {
              const errorMessage =
                error instanceof Error ? error.message : 'Unknown parsing error'
              console.error('=== Error handling message:', errorMessage, '===')
              set({
                error: {
                  code: 'MESSAGE_PARSE_ERROR',
                  message: `Failed to parse server message: ${errorMessage}`,
                  timestamp: new Date().toISOString(),
                },
              })
              // Don't let message handling errors close the connection
              // Just log and continue
            }
          }

          ws.onerror = () => {
            set({
              connectionState: ConnectionStateEnum.ERROR,
              error: {
                code: 'WEBSOCKET_ERROR',
                message: 'WebSocket connection error occurred',
                timestamp: new Date().toISOString(),
              },
            })
          }

          ws.onclose = () => {
            const { wsConnection, reconnect } = get()
            set({ connectionState: ConnectionStateEnum.DISCONNECTED })

            // Attempt reconnection if not manually disconnected
            if (
              wsConnection.reconnectAttempts < MAX_RECONNECT_ATTEMPTS &&
              wsConnection.reconnectTimeout === null
            ) {
              reconnect()
            }
          }

          set({
            wsConnection: {
              ws,
              reconnectAttempts: 0,
              reconnectTimeout: null,
            },
          })
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Unknown error'
          set({
            connectionState: ConnectionStateEnum.ERROR,
            error: {
              code: 'CONNECTION_FAILED',
              message: `Failed to connect to WebSocket: ${errorMessage}`,
              timestamp: new Date().toISOString(),
            },
          })
        }
      },

      /**
       * Disconnect from the WebSocket server.
       */
      disconnect: () => {
        const { wsConnection } = get()

        if (wsConnection.reconnectTimeout) {
          clearTimeout(wsConnection.reconnectTimeout)
        }

        if (wsConnection.ws) {
          wsConnection.ws.close()
        }

        set({
          connectionState: ConnectionStateEnum.DISCONNECTED,
          wsConnection: {
            ws: null,
            reconnectAttempts: 0,
            reconnectTimeout: null,
          },
        })
      },

      /**
       * Attempt to reconnect to the WebSocket server.
       */
      reconnect: () => {
        const { wsConnection } = get()

        if (wsConnection.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
          set({
            error: {
              code: 'MAX_RECONNECT_ATTEMPTS',
              message: 'Maximum reconnection attempts reached',
              timestamp: new Date().toISOString(),
            },
          })
          return
        }

        const delay = RECONNECT_DELAY_MS * Math.pow(2, wsConnection.reconnectAttempts)

        set({
          connectionState: ConnectionStateEnum.RECONNECTING,
          wsConnection: {
            ...wsConnection,
            reconnectAttempts: wsConnection.reconnectAttempts + 1,
          },
        })

        const timeoutId = setTimeout(() => {
          const currentUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:5173/ws/debate'
          get().connect(currentUrl)
        }, delay)

        set({
          wsConnection: {
            ...wsConnection,
            reconnectTimeout: timeoutId,
          },
        })
      },

      /**
       * Handle incoming server messages.
       */
      handleServerMessage: (message: ServerMessage) => {
        console.log('=== Handling server message:', message.type, '===')
        switch (message.type) {
          case 'agent_message':
            console.log('=== Adding agent message ===')
            get().addMessage(message)
            break

          case 'tree_update':
            console.log('=== Updating conversation tree ===')
            get().updateConversationTree(message)
            break

          case 'interrupt_acknowledged':
            console.log('=== Interrupt acknowledged ===')
            set({
              isInterrupted: true,
              streamState: StreamStateEnum.INTERRUPTED,
            })
            break

          case 'stream_end':
            console.log('=== Stream ended ===')
            set({
              streamState: StreamStateEnum.ENDED,
            })
            break

          case 'agent_input_request':
            console.log('=== Agent input request received ===')
            set({
              agentInputRequest: message,
              streamState: StreamStateEnum.WAITING_FOR_AGENT_INPUT,
            })
            break

          case 'error':
            console.log('=== Error message received ===')
            set({
              error: {
                code: message.error_code,
                message: message.message,
                timestamp: message.timestamp,
              },
            })
            break

          default:
            // Log unhandled message types but don't throw to avoid closing connection
            console.error(`=== Unhandled message type: ${(message as any).type} ===`, message)
            set({
              error: {
                code: 'UNHANDLED_MESSAGE_TYPE',
                message: `Received unhandled message type: ${(message as any).type}`,
                timestamp: new Date().toISOString(),
              },
            })
        }
      },

      /**
       * Add a new agent message to the messages array.
       */
      addMessage: (message: AgentMessage) => {
        set((state) => ({
          messages: [...state.messages, message],
          activeNodeId: message.node_id,
          streamState: StreamStateEnum.STREAMING,
        }))
      },

      /**
       * Update the conversation tree with new data from server.
       */
      updateConversationTree: (treeUpdate: TreeUpdate) => {
        set({
          conversationTree: treeUpdate.root,
          currentBranchId: treeUpdate.current_branch_id,
        })
      },

      /**
       * Send a user message to a specific agent.
       */
      sendUserMessage: (content: string, targetAgent: string, trimCount: number) => {
        const { wsConnection, connectionState } = get()

        if (connectionState !== ConnectionStateEnum.CONNECTED || !wsConnection.ws) {
          throw new Error('WebSocket is not connected')
        }

        if (!content.trim()) {
          throw new Error('Message content cannot be empty')
        }

        if (!targetAgent.trim()) {
          throw new Error('Target agent must be specified')
        }

        const message: UserDirectedMessage = {
          type: 'user_directed_message' as MessageType.USER_DIRECTED_MESSAGE,
          content: content.trim(),
          target_agent: targetAgent.trim(),
          trim_count: trimCount,
          timestamp: new Date().toISOString(),
        }

        wsConnection.ws.send(JSON.stringify(message))

        // Reset user interaction state
        set({
          userMessageDraft: '',
          trimCount: 0,
          isInterrupted: false,
          streamState: StreamStateEnum.STREAMING,
        })
      },

      /**
       * Send an interrupt request to pause the agent stream.
       */
      sendInterrupt: () => {
        const { wsConnection, connectionState, streamState } = get()

        if (connectionState !== ConnectionStateEnum.CONNECTED || !wsConnection.ws) {
          throw new Error('WebSocket is not connected')
        }

        if (streamState !== StreamStateEnum.STREAMING) {
          throw new Error('Cannot interrupt when stream is not active')
        }

        const message: UserInterrupt = {
          type: 'user_interrupt' as MessageType.USER_INTERRUPT,
          timestamp: new Date().toISOString(),
        }

        wsConnection.ws.send(JSON.stringify(message))
      },

      /**
       * Set the selected agent for user messages.
       */
      setSelectedAgent: (agentName: string | null) => {
        set({ selectedAgent: agentName })
      },

      /**
       * Set the trim count for branching.
       */
      setTrimCount: (count: number) => {
        if (count < 0) {
          throw new Error('Trim count cannot be negative')
        }
        set({ trimCount: count })
      },

      /**
       * Set the user message draft.
       */
      setUserMessageDraft: (draft: string) => {
        set({ userMessageDraft: draft })
      },

      /**
       * Send an agent input response to the backend.
       * Note: Empty strings are allowed (e.g., when user cancels the input request).
       */
      sendAgentInputResponse: (requestId: string, userInput: string) => {
        const { wsConnection, connectionState } = get()

        if (connectionState !== ConnectionStateEnum.CONNECTED || !wsConnection.ws) {
          throw new Error('WebSocket is not connected')
        }

        // Allow empty strings for cancel functionality
        const message: AgentInputResponse = {
          type: 'agent_input_response' as MessageType.AGENT_INPUT_RESPONSE,
          request_id: requestId,
          user_input: userInput.trim(),
          timestamp: new Date().toISOString(),
        }

        wsConnection.ws.send(JSON.stringify(message))

        // Clear agent input state and resume streaming
        set({
          agentInputRequest: null,
          agentInputDraft: '',
          streamState: StreamStateEnum.STREAMING,
        })
      },

      /**
       * Set the agent input draft.
       */
      setAgentInputDraft: (draft: string) => {
        set({ agentInputDraft: draft })
      },

      /**
       * Clear the agent input request (e.g., on cancel).
       */
      clearAgentInputRequest: () => {
        set({
          agentInputRequest: null,
          agentInputDraft: '',
        })
      },

      /**
       * Set the stream state.
       */
      setStreamState: (state: StreamState) => {
        set({ streamState: state })
      },

      /**
       * Set the interrupted flag.
       */
      setInterrupted: (interrupted: boolean) => {
        set({ isInterrupted: interrupted })
      },

      /**
       * Set an error.
       */
      setError: (error: AppError | null) => {
        set({ error })
      },

      /**
       * Clear the current error.
       */
      clearError: () => {
        set({ error: null })
      },

      /**
       * Reset the store to initial state.
       */
      reset: () => {
        const { disconnect } = get()
        disconnect()
        set(initialState)
      },
    }),
    {
      name: 'debate-store',
    }
  )
)
