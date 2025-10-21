/**
 * Typed hooks for using the research store.
 *
 * These hooks provide convenient, type-safe access to specific parts
 * of the research store state and actions.
 */

import { useResearchStore } from '../store/researchStore'
import type {
  AgentMessage,
  AppError,
  ConnectionState,
  StreamState,
  TreeNode,
} from '../types'

/**
 * Hook to access WebSocket connection state.
 */
export function useConnectionState(): ConnectionState {
  return useResearchStore((state) => state.connectionState)
}

/**
 * Hook to check if WebSocket is connected.
 */
export function useIsConnected(): boolean {
  return useResearchStore((state) => state.connectionState === 'connected')
}

/**
 * Hook to access all conversation messages.
 */
export function useMessages(): AgentMessage[] {
  return useResearchStore((state) => state.messages)
}

/**
 * Hook to access the conversation tree.
 */
export function useConversationTree(): TreeNode | null {
  return useResearchStore((state) => state.conversationTree)
}

/**
 * Hook to access the current branch ID.
 */
export function useCurrentBranchId(): string {
  return useResearchStore((state) => state.currentBranchId)
}

/**
 * Hook to access the active node ID.
 */
export function useActiveNodeId(): string | null {
  return useResearchStore((state) => state.activeNodeId)
}

/**
 * Hook to access stream state.
 */
export function useStreamState(): StreamState {
  return useResearchStore((state) => state.streamState)
}

/**
 * Hook to check if stream is interrupted.
 */
export function useIsInterrupted(): boolean {
  return useResearchStore((state) => state.isInterrupted)
}

/**
 * Hook to check if stream is actively streaming.
 */
export function useIsStreaming(): boolean {
  return useResearchStore((state) => state.streamState === 'streaming')
}

/**
 * Hook to access selected agent for user messages.
 */
export function useSelectedAgent(): string | null {
  return useResearchStore((state) => state.selectedAgent)
}

/**
 * Hook to access trim count.
 */
export function useTrimCount(): number {
  return useResearchStore((state) => state.trimCount)
}

/**
 * Hook to access user message draft.
 */
export function useUserMessageDraft(): string {
  return useResearchStore((state) => state.userMessageDraft)
}

/**
 * Hook to access current error state.
 */
export function useError(): AppError | null {
  return useResearchStore((state) => state.error)
}

/**
 * Hook to access WebSocket connection actions.
 */
export function useConnectionActions() {
  return useResearchStore((state) => ({
    connect: state.connect,
    disconnect: state.disconnect,
    reconnect: state.reconnect,
  }))
}

/**
 * Hook to access message sending actions.
 */
export function useMessageActions() {
  return useResearchStore((state) => ({
    sendUserMessage: state.sendUserMessage,
    sendInterrupt: state.sendInterrupt,
  }))
}

/**
 * Hook to access user interaction state setters.
 */
export function useUserInteractionActions() {
  return useResearchStore((state) => ({
    setSelectedAgent: state.setSelectedAgent,
    setTrimCount: state.setTrimCount,
    setUserMessageDraft: state.setUserMessageDraft,
  }))
}

/**
 * Hook to access error management actions.
 */
export function useErrorActions() {
  return useResearchStore((state) => ({
    setError: state.setError,
    clearError: state.clearError,
  }))
}

/**
 * Hook to access store reset action.
 */
export function useResetStore() {
  return useResearchStore((state) => state.reset)
}

/**
 * Hook to access all store state (use sparingly to avoid unnecessary re-renders).
 */
export function useResearchStoreState() {
  return useResearchStore((state) => ({
    connectionState: state.connectionState,
    messages: state.messages,
    conversationTree: state.conversationTree,
    currentBranchId: state.currentBranchId,
    activeNodeId: state.activeNodeId,
    streamState: state.streamState,
    isInterrupted: state.isInterrupted,
    selectedAgent: state.selectedAgent,
    trimCount: state.trimCount,
    userMessageDraft: state.userMessageDraft,
    error: state.error,
  }))
}

/**
 * Hook to access all store actions (use for convenience when multiple actions are needed).
 */
export function useResearchStoreActions() {
  return useResearchStore((state) => ({
    connect: state.connect,
    disconnect: state.disconnect,
    reconnect: state.reconnect,
    sendUserMessage: state.sendUserMessage,
    sendInterrupt: state.sendInterrupt,
    setSelectedAgent: state.setSelectedAgent,
    setTrimCount: state.setTrimCount,
    setUserMessageDraft: state.setUserMessageDraft,
    setStreamState: state.setStreamState,
    setInterrupted: state.setInterrupted,
    setError: state.setError,
    clearError: state.clearError,
    reset: state.reset,
  }))
}

/**
 * Hook to access agent input request state.
 */
export function useAgentInputRequest() {
  return useResearchStore((state) => state.agentInputRequest)
}

/**
 * Hook to access agent input draft.
 */
export function useAgentInputDraft() {
  return useResearchStore((state) => state.agentInputDraft)
}

/**
 * Hook to access agent input actions.
 */
export function useAgentInputActions() {
  return useResearchStore((state) => ({
    sendAgentInputResponse: state.sendAgentInputResponse,
    setAgentInputDraft: state.setAgentInputDraft,
    clearAgentInputRequest: state.clearAgentInputRequest,
  }))
}

/**
 * Hook to access streaming chunks accumulated for a specific node.
 */
export function useStreamingChunksForNode(nodeId: string): string {
  return useResearchStore((state) => state.streamingChunksByNodeId[nodeId] || '')
}

/**
 * Hook to access all streaming chunks buffer.
 */
export function useStreamingChunksBuffer(): Record<string, string> {
  return useResearchStore((state) => state.streamingChunksByNodeId)
}

/**
 * Hook to access current streaming node ID.
 */
export function useCurrentStreamingNodeId(): string | null {
  return useResearchStore((state) => state.currentStreamingNodeId)
}
