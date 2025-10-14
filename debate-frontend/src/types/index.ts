/**
 * TypeScript types matching backend Pydantic models.
 *
 * These types mirror the models defined in debate-backend/models.py
 * to ensure type safety across the WebSocket communication layer.
 */

/**
 * WebSocket message types for client-server communication.
 */
export enum MessageType {
  AGENT_MESSAGE = 'agent_message',
  USER_INTERRUPT = 'user_interrupt',
  USER_DIRECTED_MESSAGE = 'user_directed_message',
  INTERRUPT_ACKNOWLEDGED = 'interrupt_acknowledged',
  STREAM_END = 'stream_end',
  ERROR = 'error',
  TREE_UPDATE = 'tree_update',
}

/**
 * Base interface for all WebSocket messages.
 */
interface BaseMessage {
  type: MessageType
  timestamp: string
}

/**
 * Message sent from an agent during the debate conversation.
 */
export interface AgentMessage extends BaseMessage {
  type: MessageType.AGENT_MESSAGE
  agent_name: string
  content: string
  node_id: string
}

/**
 * Request from client to interrupt the agent conversation stream.
 */
export interface UserInterrupt extends BaseMessage {
  type: MessageType.USER_INTERRUPT
}

/**
 * Message from user directed to a specific agent with optional thread trimming.
 */
export interface UserDirectedMessage extends BaseMessage {
  type: MessageType.USER_DIRECTED_MESSAGE
  content: string
  target_agent: string
  trim_count: number
}

/**
 * Acknowledgment that the interrupt was successful and ready for user input.
 */
export interface InterruptAcknowledged extends BaseMessage {
  type: MessageType.INTERRUPT_ACKNOWLEDGED
  message: string
}

/**
 * Notification that the agent conversation stream has ended.
 */
export interface StreamEnd extends BaseMessage {
  type: MessageType.STREAM_END
  reason: string
}

/**
 * Error notification sent to client.
 */
export interface ErrorMessage extends BaseMessage {
  type: MessageType.ERROR
  error_code: string
  message: string
}

/**
 * A node in the conversation tree representing a single message.
 */
export interface TreeNode {
  id: string
  agent_name: string
  message: string
  parent: string | null
  children: TreeNode[]
  is_active: boolean
  branch_id: string
  timestamp: string
}

/**
 * Complete tree structure update sent to client.
 */
export interface TreeUpdate extends BaseMessage {
  type: MessageType.TREE_UPDATE
  root: TreeNode
  current_branch_id: string
}

/**
 * Union type of all possible WebSocket messages from server.
 */
export type ServerMessage =
  | AgentMessage
  | InterruptAcknowledged
  | StreamEnd
  | ErrorMessage
  | TreeUpdate

/**
 * Union type of all possible WebSocket messages sent to server.
 */
export type ClientMessage = UserInterrupt | UserDirectedMessage

/**
 * WebSocket connection state.
 */
export enum ConnectionState {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
}

/**
 * Stream state tracking whether agents are actively conversing.
 */
export enum StreamState {
  IDLE = 'idle',
  STREAMING = 'streaming',
  INTERRUPTED = 'interrupted',
  ENDED = 'ended',
}

/**
 * Agent names from the debate team.
 */
export enum AgentName {
  JARA_SUPPORTER = 'Jara_Supporter',
  KAST_SUPPORTER = 'Kast_Supporter',
  NEURAL_AGENT = 'Neural_Agent',
  MODERATE_LEFT = 'Moderate_Left',
  MODERATE_RIGHT = 'Moderate_Right',
  USER = 'User',
  SYSTEM = 'System',
}

/**
 * Configuration for agent display.
 */
export interface AgentConfig {
  name: AgentName
  displayName: string
  color: string
  description: string
}

/**
 * Error state for the application.
 */
export interface AppError {
  code: string
  message: string
  timestamp: string
}
