/**
 * Zustand store for managing the application state of the agent team
 * This store manages:
 * 1. The state of the WebSocket connection
 * 2. The messages in the conversation
 * 3. The data of the conversation tree created by the human-agent interaction
 * 4. The state of interruption and the concrete human-agent interactions
 * 5. The trim count for branching
 */

import {create} from 'zustand'
import {devtools} from 'zustand/middleware'

import type {
    RunConfig,
    AgentTeamNames,
    AgentDetails,
    ParticipantNames,
    AgentInputRequest,
    HumanInputResponse,
    AgentMessage,
    ConnectionState,
    ServerMessage,
    StreamState,
    ToolCall,
    ToolExecution,
    TreeNode,
    TreeUpdate,
    UserDirectedMessage,
    UserInterrupt,
    AppError,
    ChatFocusTarget,
} from '../types'

import {
    MessageType,
    ConnectionState as ConnectionStateEnum,
    StreamState as StreamStateEnum,
} from '../types'


interface WebSocketConnection {
    ws: WebSocket | null
    reconnectAttempts: number
    reconnectTimeout: ReturnType<typeof setTimeout> | null
}

interface State {
    connectionState: ConnectionState
    wsConnection: WebSocketConnection

    // Agent Team Names received from backend
    agent_names: AgentTeamNames | null

    // Agent Details (names and descriptions) received from backend
    agent_details: AgentDetails | null

    // Participant Names (individual agents) received from backend
    participant_names: ParticipantNames | null

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

    // Edge interrupt state (for clicking edges to branch)
    edgeInterrupt: {
        targetNodeId: string
        position: { x: number; y: number }
        trimCount: number
    } | null

    // Agent input request state
    agentInputRequest: AgentInputRequest | null
    humanInputDraft: string

    // Tool call tracking
    toolCallsByNodeId: Record<string, ToolCall>
    toolExecutionsByNodeId: Record<string, ToolExecution>

    // Chat display state
    isChatDisplayVisible: boolean
    selectedNodeIdForChat: string | null
    chatFocusTarget: ChatFocusTarget | null

    // Error state
    error: AppError | null

    // Below are the functions that are used to manage (add/remove/update) different fields of our above-defined
    // Zustand state


    // Actions: WebSocket management
    connect: (url: string) => void
    sendConfig: (config: RunConfig) => void
    disconnect: () => void
    reconnect: () => void

    // Actions: Agent Team Name Setting
    setAgentTeamNames: (agentTeamNames: AgentTeamNames) => void
    setAgentDetails: (agentDetails: AgentDetails) => void
    setParticipantNames: (participantNames: ParticipantNames) => void

    // Actions: Message handling
    handleServerMessage: (message: ServerMessage) => void // this is where we do case distinction on the aggregate type ServerMessage
    addMessage: (message: AgentMessage) => void
    updateConversationTree: (treeUpdate: TreeUpdate) => void

    // Actions: Human-Agent interaction (UserControlAgent)
    sendUserMessage: (content: string, targetAgent: string, trimCount: number) => void
    sendInterrupt: () => void
    setSelectedAgent: (agentName: string | null) => void
    setTrimCount: (count: number) => void
    setUserMessageDraft: (draft: string) => void

    // Actions: Edge interrupt management
    setEdgeInterrupt: (targetNodeId: string, position: { x: number; y: number }, trimCount: number) => void
    clearEdgeInterrupt: () => void

    // Actions: Human-Agent interaction (UserProxyAgent)
    sendHumanInputResponse: (requestId: string, userInput: string) => void
    setHumanInputDraft: (draft: string) => void
    clearAgentInputRequest: () => void

    // Actions: Toggling state variables
    setStreamState: (state: StreamState) => void
    setInterrupted: (interrupted: boolean) => void
    setChatDisplayVisible: (visible: boolean) => void
    setSelectedNodeIdForChat: (nodeId: string | null) => void
    setChatFocusTarget: (target: ChatFocusTarget | null) => void
    setError: (error: AppError | null) => void
    clearError: () => void
    reset: () => void
}

const initialState = {
    connectionState: ConnectionStateEnum.DISCONNECTED,
    wsConnection: {
        ws: null,
        reconnectAttempts: 0,
        reconnectTimeout: null,
    },
    agent_names: null as AgentTeamNames | null,
    agent_details: null as AgentDetails | null,
    participant_names: null as ParticipantNames | null,
    messages: [],
    conversationTree: null,
    currentBranchId: 'main',
    activeNodeId: null,
    streamState: StreamStateEnum.IDLE,
    isInterrupted: false,
    selectedAgent: null,
    trimCount: 0,
    userMessageDraft: '',
    edgeInterrupt: null,
    agentInputRequest: null,
    humanInputDraft: '',
    toolCallsByNodeId: {},
    toolExecutionsByNodeId: {},
    isChatDisplayVisible: false,  // Hidden by default, shows when summary is clicked
    selectedNodeIdForChat: null,
    chatFocusTarget: null,
    error: null
}

// We reconnect at most 5 times, trying with exponential frequency (1, 2, 4, 8.. seconds)
const MAX_RECONNECT_ATTEMPTS = 5
const RECONNECT_DELAY_MS = 1000

export const useStore = create<State>()(
    devtools(
        (set, get) => ({
            ...initialState,

            // Connect to WebSocket server (does NOT send config - that comes later)
            connect: (url: string) => {
                const {wsConnection, disconnect} = get()

                // If there is already an existing connection: close it
                if (wsConnection.ws) {
                    disconnect()
                }

                set({
                    connectionState: ConnectionStateEnum.CONNECTING,
                    agent_names: null,
                    messages: [],
                    conversationTree: null,
                    currentBranchId: 'main',
                    activeNodeId: null,
                    toolCallsByNodeId: {},
                    toolExecutionsByNodeId: {},
                    isInterrupted: false,
                    streamState: StreamStateEnum.IDLE,
                    agentInputRequest: null,
                    humanInputDraft: '',
                    error: null,
                    selectedAgent: null,
                    trimCount: 0,
                    userMessageDraft: '',
                    edgeInterrupt: null,
                })

                try {
                    const ws = new WebSocket(url)

                    ws.onopen = () => {
                        console.log('=== WebSocket connected, waiting for agent team names ===')

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

                    // what we do when we recieve a message
                    ws.onmessage = (event: MessageEvent) => {
                        try {
                            const message: ServerMessage = JSON.parse(event.data)
                            get().handleServerMessage(message)
                        } catch (error) {
                            const errorMessage = error instanceof Error ? error.message : 'Unknown parsing error'
                            
                            set({
                                error: {
                                    code: 'MESSAGE_PARSE_ERROR',
                                    message: `Failed to parse server message: ${errorMessage}`,
                                    timestamp: new Date().toISOString(),
                                }
                            })

                            // message handling errors shouldn't close the connection
                            // we log and continue

                        }
                    }

                    ws.onerror = () => {
                        set({
                            connectionState: ConnectionStateEnum.ERROR,
                            error: {
                                code: 'WEBSOCKET_ERROR',
                                message: 'WebSocket connection error occured',
                                timestamp: new Date().toISOString(),
                            }
                        })
                    }

                    ws.onclose = () => {
                        const {wsConnection, reconnect} = get()
                        set({ connectionState: ConnectionStateEnum.DISCONNECTED})

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
                            timestamp: new Date().toISOString()
                        },
                    })

                }
            },

            // Send config to backend after receiving agent team names
            sendConfig: (config: RunConfig) => {
                const {wsConnection, connectionState} = get()

                if (connectionState !== ConnectionStateEnum.CONNECTED || !wsConnection.ws) {
                    throw new Error('WebSocket is not connected')
                }

                console.log('=== Sending config to backend ===', config)
                wsConnection.ws.send(JSON.stringify(config))
            },

            // disconnecting
            disconnect: () => {
                const { wsConnection } = get()

                if (wsConnection.reconnectTimeout) {
                    clearTimeout(wsConnection.reconnectTimeout)
                }

                // Set reconnectAttempts to MAX to prevent auto-reconnection
                set({
                    wsConnection: {
                        ...wsConnection,
                        reconnectAttempts: MAX_RECONNECT_ATTEMPTS,
                        reconnectTimeout: null,
                    },
                })

                if (wsConnection.ws) {
                    wsConnection.ws.close()
                }

                set({
                    connectionState: ConnectionStateEnum.DISCONNECTED,
                })
            },

            reconnect: () => {
                const {wsConnection} = get()

                if (wsConnection.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
                    set({
                        error: {
                            code: 'MAX_RECONNECT_ATTEMPTS',
                            message: 'Maximum reconnection attempts reached',
                            timestamp: new Date().toISOString(),
                        }
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
                    const currentUrl = import.meta.env.VITE_WS_URL
                    get().connect(currentUrl)
                }, delay)

                set({
                    wsConnection: {
                        ...wsConnection,
                        reconnectTimeout: timeoutId
                    },
                })
            },

            handleServerMessage: (message: ServerMessage) => {

                switch (message.type) {

                    case 'agent_team_names':
                        get().setAgentTeamNames(message)
                        break

                    case 'agent_details':
                        get().setAgentDetails(message)
                        break

                    case 'participant_names':
                        get().setParticipantNames(message)
                        break

                    case 'agent_message':
                        get().addMessage(message)
                        break

                    case 'tree_update':
                        get().updateConversationTree(message)
                        break
                    
                    case 'interrupt_acknowledged':
                        set({
                            isInterrupted: true,
                            streamState: StreamStateEnum.INTERRUPTED,
                            agentInputRequest: null,
                        })
                        break
                    
                    case 'stream_end':
                        set({
                            streamState: StreamStateEnum.ENDED
                        })
                        break
                    
                    case 'agent_input_request':
                        set({
                            agentInputRequest: message,
                            streamState: StreamStateEnum.WAITING_FOR_AGENT_INPUT
                        })
                        break
                    
                    case 'error':
                        set({
                            error: {
                                code: message.error_code,
                                message: message.message,
                                timestamp: message.timestamp,
                            }
                        })
                        break
                    
                    case 'tool_call':
                        set((state) => ({
                            toolCallsByNodeId: {
                                ...state.toolCallsByNodeId,
                                [message.node_id]: message
                            },
                        }))
                        break

                    case 'tool_execution':

                        set((state) => ({
                            toolExecutionsByNodeId: {
                                ...state.toolExecutionsByNodeId,
                                [message.node_id]: message,
                            },
                        }))
                        break

                    default:
                        set({
                            error: {
                                code: 'UNHANDLED+MESSAGE_TYPE',
                                message: `Recieved unhandled message type: ${(message as any).type}`,
                                timestamp: new Date().toISOString(),
                            },
                        })
                }
            },

            setAgentTeamNames: (agentTeamNames: AgentTeamNames) => {
                set({agent_names: agentTeamNames})
            },

            setAgentDetails: (agentDetails: AgentDetails) => {
                set({agent_details: agentDetails})
            },

            setParticipantNames: (participantNames: ParticipantNames) => {
                set({participant_names: participantNames})
            },

            addMessage: (message: AgentMessage) => {
                console.log('[Store] addMessage called', {
                    node_id: message.node_id,
                    agent_name: message.agent_name,
                    content_length: message.content.length,
                    content_preview: message.content.substring(0, 100)
                })

                set((state) => ({
                    messages: [...state.messages, message],
                    activeNodeId: message.node_id,
                    streamState: StreamStateEnum.STREAMING,
                }))
            },

            updateConversationTree: (treeUpdate: TreeUpdate) => {
                set({
                    conversationTree: treeUpdate.root,
                    currentBranchId: treeUpdate.current_branch_id,
                })
            },

            sendUserMessage: (content: string, targetAgent: string, trimCount: number) => {
                const {wsConnection, connectionState} = get()

                if (connectionState !== ConnectionStateEnum.CONNECTED || !wsConnection.ws ) {
                    throw new Error('WebSocket is not connected')
                }
                if (!content.trim()) {
                    throw new Error('Message content cannot be empty')
                }
        
                if (!targetAgent.trim()) {
                    throw new Error('Target agent must be specified')
                }

                const message: UserDirectedMessage = {
                    type: MessageType.USER_DIRECTED_MESSAGE,
                    content: content.trim(),
                    target_agent: targetAgent.trim(),
                    trim_count: trimCount,
                    timestamp: new Date().toISOString()
                }

                wsConnection.ws.send(JSON.stringify(message))

                set({
                    userMessageDraft: '',
                    trimCount: 0,
                    isInterrupted: false,
                    streamState: StreamStateEnum.STREAMING,
                    edgeInterrupt: null,
                })
            },

            sendInterrupt: () => {
                const {wsConnection, connectionState, streamState} = get()

                if (connectionState !== ConnectionStateEnum.CONNECTED || !wsConnection.ws) {
                    throw new Error('WebSocket is not connected')
                }
        
                if (streamState !== StreamStateEnum.STREAMING) {
                    throw new Error('Cannot interrupt when stream is not active')
                }

                const message: UserInterrupt = {
                    type: MessageType.USER_INTERRUPT,
                    timestamp: new Date().toISOString()
                }

                wsConnection.ws.send(JSON.stringify(message))

            },

            setSelectedAgent: (agentName: string | null) => {
                set({selectedAgent: agentName})
            },

            setTrimCount: (count: number) => {
                if (count < 0) {
                    throw new Error('Trim count cannot be negative')
                }
                set({trimCount: count})
            },

            setUserMessageDraft: (draft: string) => {
                set({userMessageDraft: draft})
            },

            setEdgeInterrupt: (targetNodeId: string, position: { x: number; y: number }, trimCount: number) => {
                set({
                    edgeInterrupt: {
                        targetNodeId,
                        position,
                        trimCount,
                    },
                })
            },

            clearEdgeInterrupt: () => {
                set({edgeInterrupt: null})
            },

            sendHumanInputResponse: (requestId: string, userInput: string) => {
                const {wsConnection, connectionState} = get()

                if (connectionState !== ConnectionStateEnum.CONNECTED || !wsConnection.ws) {
                    throw new Error('WebSocket is not connected')
                }

                const message: HumanInputResponse = {
                    type: MessageType.HUMAN_INPUT_RESPONSE,
                    request_id: requestId,
                    user_input: userInput.trim(),
                    timestamp: new Date().toISOString()
                }

                wsConnection.ws.send(JSON.stringify(message))

                set({
                    agentInputRequest: null,
                    humanInputDraft: '',
                    streamState: StreamStateEnum.STREAMING,
                })
            },

            setHumanInputDraft: (draft: string) => {
                set({humanInputDraft: draft})
            },

            clearAgentInputRequest: () => {
                set({
                    agentInputRequest: null,
                    humanInputDraft: '',
                })
            },

            setStreamState: (state: StreamState) => {
                set({streamState: state})
            },

            setInterrupted: (interrupted: boolean) => {
                set({isInterrupted: interrupted})
            },

            setChatDisplayVisible: (visible: boolean) => {
                set({isChatDisplayVisible: visible})
            },

            setSelectedNodeIdForChat: (nodeId: string | null) => {
                set({
                    selectedNodeIdForChat: nodeId,
                    chatFocusTarget: nodeId ? { nodeId, itemType: 'message' } : null,
                })
            },

            setChatFocusTarget: (target: ChatFocusTarget | null) => {
                set({
                    chatFocusTarget: target,
                    selectedNodeIdForChat: target ? target.nodeId : null,
                })
            },

            setError: (error: AppError | null ) => {
                set({error})
            },

            clearError: () => {
                set({ error: null})
            },

            reset: () => {
                const {disconnect} = get()
                disconnect()
                set(initialState)
            },

        }),
        {
            name: 'store',
        }
    )
)
