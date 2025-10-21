/**
 * Zustand store for managing research application state.
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
  ResearchConfig,
  ServerMessage,
  StreamingChunk,
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
 * Research store state interface.
 */
interface ResearchState {
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

  // Streaming chunks accumulation
  streamingChunksByNodeId: Record<string, string>
  currentStreamingNodeId: string | null

  // Error state
  error: AppError | null

  // Actions: WebSocket management
  connect: (url: string) => void
  disconnect: () => void
  reconnect: () => void

  // Actions: Message handling
  handleServerMessage: (message: ServerMessage) => void
  addMessage: (message: AgentMessage) => void
  appendStreamingChunk: (chunk: StreamingChunk) => void
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
  streamingChunksByNodeId: {},
  currentStreamingNodeId: null,
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
 * Create the research store with devtools for debugging.
 */
export const useResearchStore = create<ResearchState>()(
  devtools(
    (set, get) => ({
      ...initialState,

      /**
       * Connect to the WebSocket server.
       */
      connect: (url: string, config?: ResearchConfig) => {
        const { wsConnection, disconnect } = get()

        // Close existing connection if any
        if (wsConnection.ws) {
          disconnect()
        }

        // Clear all previous conversation data when starting a new session
        // But keep user interaction state (selectedAgent, trimCount, userMessageDraft)
        set({
          connectionState: ConnectionStateEnum.CONNECTING,
          messages: [],
          conversationTree: null,
          currentBranchId: 'main',
          activeNodeId: null,
          streamingChunksByNodeId: {},
          currentStreamingNodeId: null,
          isInterrupted: false,
          streamState: StreamStateEnum.IDLE,
          agentInputRequest: null,
          agentInputDraft: '',
          error: null,
          // Keep user interaction state
          selectedAgent: get().selectedAgent,
          trimCount: 0,
          userMessageDraft: get().userMessageDraft,
        })

        try {
          const ws = new WebSocket(url)

          ws.onopen = () => {
            // Send config immediately after connection establishes
            if (config) {
              console.log('=== Sending research config ===')
              ws.send(JSON.stringify(config))
            }

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
          const currentUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws/research'
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
          case 'streaming_chunk':
            console.log('=== Accumulating streaming chunk ===')
            get().appendStreamingChunk(message)
            break

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
       * Handles the transition from streaming to final message.
       * Replaces temporary streaming message with final message.
       */
      addMessage: (message: AgentMessage) => {
        set((state) => {
          // Don't merge chunks - the final message already contains complete content
          const finalMessage = { ...message }

          // Find and replace any temporary streaming message from this agent
          // Streaming messages use temporary node IDs like "node_stream_xxx"
          const streamingMsgIndex = state.messages.findIndex(
            (msg) =>
              msg.agent_name === message.agent_name &&
              msg.node_id.startsWith('node_stream_')
          )

          let updatedMessages = state.messages
          if (streamingMsgIndex !== -1) {
            // Replace the temporary streaming message with the final message
            updatedMessages = [...state.messages]
            updatedMessages[streamingMsgIndex] = finalMessage
          } else {
            // Check if message with same node_id already exists (shouldn't happen)
            const existingIndex = state.messages.findIndex(
              (msg) => msg.node_id === message.node_id
            )
            if (existingIndex === -1) {
              // Add new message
              updatedMessages = [...state.messages, finalMessage]
            } else {
              // Update existing message (edge case)
              updatedMessages = [...state.messages]
              updatedMessages[existingIndex] = finalMessage
            }
          }

          // Clear streaming state for this agent
          const updatedChunks = { ...state.streamingChunksByNodeId }
          // Clear any temporary streaming node IDs for this agent
          Object.keys(updatedChunks).forEach((nodeId) => {
            if (nodeId.startsWith('node_stream_')) {
              delete updatedChunks[nodeId]
            }
          })

          return {
            messages: updatedMessages,
            activeNodeId: message.node_id,
            streamState: StreamStateEnum.STREAMING,
            streamingChunksByNodeId: updatedChunks,
            currentStreamingNodeId: null,
          }
        })
      },

      /**
       * Append a streaming chunk to the current node's accumulated text.
       * Creates or updates a message as chunks accumulate for live display.
       * Works with temporary node IDs (node_stream_xxx) during streaming.
       */
      appendStreamingChunk: (chunk: StreamingChunk) => {
        set((state) => {
          const nodeId = chunk.node_id
          const currentText = state.streamingChunksByNodeId[nodeId] || ''
          const newText = currentText + chunk.content

          // Check if we already have a message for this node (temporary or otherwise)
          const existingMessageIndex = state.messages.findIndex((msg) => msg.node_id === nodeId)

          let updatedMessages = state.messages
          if (existingMessageIndex === -1) {
            // Create a new temporary message for streaming display
            const temporaryMessage: AgentMessage = {
              type: 'agent_message' as const,
              agent_name: chunk.agent_name,
              content: newText,
              node_id: nodeId, // This will be a temporary ID like node_stream_xxx
              timestamp: new Date().toISOString(),
            }
            updatedMessages = [...state.messages, temporaryMessage]
          } else {
            // Update existing message with new chunks
            updatedMessages = state.messages.map((msg) =>
              msg.node_id === nodeId ? { ...msg, content: newText } : msg
            )
          }

          return {
            messages: updatedMessages,
            streamingChunksByNodeId: {
              ...state.streamingChunksByNodeId,
              [nodeId]: newText,
            },
            currentStreamingNodeId: nodeId,
            activeNodeId: nodeId,
            streamState: StreamStateEnum.STREAMING,
          }
        })
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
      name: 'research-store',
    }
  )
)
