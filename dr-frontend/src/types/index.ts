/**
 * TypeScript types matching backend Pydantic models.
 *
 * These types mirror the models defined in dr-backend/models.py
 * to ensure type safety across the WebSocket communication layer.
 */

/**
 * WebSocket message types for client-server communication.
 */
export enum MessageType {
  START_RESEARCH = 'start_research',
  AGENT_MESSAGE = 'agent_message',
  STREAMING_CHUNK = 'streaming_chunk',
  USER_INTERRUPT = 'user_interrupt',
  USER_DIRECTED_MESSAGE = 'user_directed_message',
  INTERRUPT_ACKNOWLEDGED = 'interrupt_acknowledged',
  STREAM_END = 'stream_end',
  ERROR = 'error',
  TREE_UPDATE = 'tree_update',
  AGENT_INPUT_REQUEST = 'agent_input_request',
  AGENT_INPUT_RESPONSE = 'agent_input_response',
  TOOL_CALL = 'tool_call',
  TOOL_EXECUTION = 'tool_execution',
}

/**
 * Base interface for all WebSocket messages.
 */
interface BaseMessage {
  type: MessageType
  timestamp: string
}

/**
 * Configuration sent from frontend to start research.
 */
export interface ResearchConfig extends BaseMessage {
  type: MessageType.START_RESEARCH
  initial_topic: string
  selector_prompt?: string
}

/**
 * Message sent from an agent during the research conversation.
 */
export interface AgentMessage extends BaseMessage {
  type: MessageType.AGENT_MESSAGE
  agent_name: string
  content: string
  node_id: string
}

/**
 * Partial streaming chunk from an agent during message generation.
 */
export interface StreamingChunk extends BaseMessage {
  type: MessageType.STREAMING_CHUNK
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
 * Request from backend when an agent needs human input.
 * Role-agnostic: can be used for any agent type (UserProxyAgent, fact-checkers, etc.)
 */
export interface AgentInputRequest extends BaseMessage {
  type: MessageType.AGENT_INPUT_REQUEST
  request_id: string
  prompt: string
  agent_name: string
}

/**
 * Response from frontend with user's input to an agent request.
 */
export interface AgentInputResponse extends BaseMessage {
  type: MessageType.AGENT_INPUT_RESPONSE
  request_id: string
  user_input: string
}

/**
 * Information about a single tool/function call.
 */
export interface ToolCallInfo {
  id: string
  name: string
  arguments: string
}

/**
 * Message sent when an agent requests tool/function calls.
 */
export interface ToolCall extends BaseMessage {
  type: MessageType.TOOL_CALL
  agent_name: string
  tools: ToolCallInfo[]
  node_id: string
}

/**
 * Information about tool execution result.
 */
export interface ToolExecutionResult {
  tool_call_id: string
  tool_name: string
  success: boolean
  result: string | null
}

/**
 * Message sent when tool execution completes.
 */
export interface ToolExecution extends BaseMessage {
  type: MessageType.TOOL_EXECUTION
  agent_name: string
  results: ToolExecutionResult[]
  node_id: string
}

/**
 * Union type of all possible WebSocket messages from server.
 */
export type ServerMessage =
  | AgentMessage
  | StreamingChunk
  | InterruptAcknowledged
  | StreamEnd
  | ErrorMessage
  | TreeUpdate
  | AgentInputRequest
  | ToolCall
  | ToolExecution

/**
 * Union type of all possible WebSocket messages sent to server.
 */
export type ClientMessage = ResearchConfig | UserInterrupt | UserDirectedMessage | AgentInputResponse

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
  WAITING_FOR_AGENT_INPUT = 'waiting_for_agent_input',
  ENDED = 'ended',
}

/**
 * Agent names from the research team.
 * IMPORTANT: These must exactly match the agent names in dr-backend/research_team.py
 */
export enum AgentName {
  USER_PROXY = 'User_proxy',
  DEVELOPER = 'Developer',
  PLANNER = 'Planner',
  EXECUTOR = 'Executor',
  QUALITY_ASSURANCE = 'Quality_assurance',
  WEB_SEARCH_AGENT = 'Web_search_agent',
  REPORT_WRITER = 'Report_writer',
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
