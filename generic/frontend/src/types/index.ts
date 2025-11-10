/**
 * This file contains all the types for the WebSocket messages
 * we recieve and send from/to the backend.
 */


export enum MessageType {
    AGENT_TEAM_NAMES = 'agent_team_names',
    PARTICIPANT_NAMES = 'participant_names',
    RUN_CONFIG = 'RUN_CONFIG',
    START_RUN = 'start_run',
    AGENT_MESSAGE = 'agent_message',
    USER_INTERRUPT = 'user_interrupt',
    USER_DIRECTED_MESSAGE = 'user_directed_message',
    INTERRUPT_ACKNOWLEDGED = 'interrupt_acknowledged',
    STREAM_END = 'stream_end',
    ERROR = 'error',
    TREE_UPDATE = 'tree_update',
    AGENT_INPUT_REQUEST = 'agent_input_request',
    HUMAN_INPUT_RESPONSE = 'human_input_response',
    TOOL_CALL = 'tool_call',
    TOOL_EXECUTION = 'tool_execution',
}

/**
 * We set a base interface for all WebSocket messages.
 */
interface BaseMessage {
    type: MessageType
    timestamp: string
}

/**
 * Agent team names fixed in the YAML file in the backend that we set here in the frontend
 */
export interface AgentTeamNames extends BaseMessage {
    type: MessageType.AGENT_TEAM_NAMES
    agent_team_names: string[]
}

/**
 * Individual agent participant names in the initialized team
 */
export interface ParticipantNames extends BaseMessage {
    type: MessageType.PARTICIPANT_NAMES
    participant_names: string[]
}

/**
 * Agent team configuration that we set here in the frontend
 */
export interface RunConfig extends BaseMessage {
    type: MessageType.START_RUN
    session_id: string, // Unique session ID for this conversation (enables multi-tab support)
    initial_topic?: string, // Optional: uses backend default if not provided
    selector_prompt?: string,
    // Company-bill investigation parameters
    company_name?: string,
    bill_name?: string,
    congress?: string,
}

/**
 * This is the message that an agent generated in the team conversation
*/
export interface AgentMessage extends BaseMessage {
    type: MessageType.AGENT_MESSAGE,
    agent_name: string,
    content: string,
    summary: string,
    node_id: string,
}

/**
 * Request from client to interrupt the agent conversation stream.
 */
export interface UserInterrupt extends BaseMessage {
    type: MessageType.USER_INTERRUPT,
}

/**
 * Message from user directed to a specific agent with optional thread trimming.
 */
export interface UserDirectedMessage extends BaseMessage {
    type: MessageType.USER_DIRECTED_MESSAGE,
    content: string,
    target_agent: string,
    trim_count: number,
}

/**
 * Acknowledgment that the interrupt was successful and ready for user input.
 */
export interface InterruptAcknowledged extends BaseMessage {
    type: MessageType.INTERRUPT_ACKNOWLEDGED,
    message: string,
}

/**
 * Notification that the agent conversation stream has ended.
 */
export interface StreamEnd extends BaseMessage {
    type: MessageType.STREAM_END,
    reason: string,
}

/**
 * Error notification sent to client.
 */
export interface ErrorMessage extends BaseMessage {
    type: MessageType.ERROR,
    error_code: string,
    message: string,
}

/**
 * A node in the conversation tree representing a single message.
 */
export interface TreeNode {
    id: string,
    agent_name: string,
    message: string,
    summary: string,
    parent: string | null,
    children: TreeNode[],
    is_active: boolean,
    branch_id: string,
    timestamp: string,
    node_type: string,
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
export interface HumanInputResponse extends BaseMessage {
    type: MessageType.HUMAN_INPUT_RESPONSE
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
 * We declare this to do neat case distinction when the frontend recieves a message from the agent team.
 */
export type ServerMessage =
  | AgentTeamNames
  | ParticipantNames
  | RunConfig
  | AgentMessage
  | InterruptAcknowledged
  | StreamEnd
  | ErrorMessage
  | TreeUpdate
  | AgentInputRequest
  | ToolCall
  | ToolExecution

/**
 * Union type of all possible WebSocket messages sent to server.
 * We declare this to do neat case distinction when the frontend sends a message to the agent team.
 */
export type ClientMessage = RunConfig | UserInterrupt | UserDirectedMessage | HumanInputResponse

/**
 * State of the WebSocket connection between frontend and backend.
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
 * Error state for the application.
 */
export interface AppError {
    code: string
    message: string
    timestamp: string
  }

export type ConversationItemType = 'message' | 'tool_call' | 'tool_execution'

export interface ChatFocusTarget {
  nodeId: string
  itemType: ConversationItemType
}
