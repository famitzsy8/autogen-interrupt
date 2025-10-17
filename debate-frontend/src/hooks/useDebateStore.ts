/**
 * Typed hooks for using the debate store.
 *
 * These hooks provide convenient, type-safe access to specific parts
 * of the debate store state and actions.
 */

import { useDebateStore } from '../store/debateStore'
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
  return useDebateStore((state) => state.connectionState)
}

/**
 * Hook to check if WebSocket is connected.
 */
export function useIsConnected(): boolean {
  return useDebateStore((state) => state.connectionState === 'connected')
}

/**
 * Hook to access all conversation messages.
 */
export function useMessages(): AgentMessage[] {
  return useDebateStore((state) => state.messages)
}

/**
 * Hook to access the conversation tree.
 */
export function useConversationTree(): TreeNode | null {
  return useDebateStore((state) => state.conversationTree)
}

/**
 * Hook to access the current branch ID.
 */
export function useCurrentBranchId(): string {
  return useDebateStore((state) => state.currentBranchId)
}

/**
 * Hook to access the active node ID.
 */
export function useActiveNodeId(): string | null {
  return useDebateStore((state) => state.activeNodeId)
}

/**
 * Hook to access stream state.
 */
export function useStreamState(): StreamState {
  return useDebateStore((state) => state.streamState)
}

/**
 * Hook to check if stream is interrupted.
 */
export function useIsInterrupted(): boolean {
  return useDebateStore((state) => state.isInterrupted)
}

/**
 * Hook to check if stream is actively streaming.
 */
export function useIsStreaming(): boolean {
  return useDebateStore((state) => state.streamState === 'streaming')
}

/**
 * Hook to access selected agent for user messages.
 */
export function useSelectedAgent(): string | null {
  return useDebateStore((state) => state.selectedAgent)
}

/**
 * Hook to access trim count.
 */
export function useTrimCount(): number {
  return useDebateStore((state) => state.trimCount)
}

/**
 * Hook to access user message draft.
 */
export function useUserMessageDraft(): string {
  return useDebateStore((state) => state.userMessageDraft)
}

/**
 * Hook to access current error state.
 */
export function useError(): AppError | null {
  return useDebateStore((state) => state.error)
}

/**
 * Hook to access WebSocket connection actions.
 */
export function useConnectionActions() {
  return useDebateStore((state) => ({
    connect: state.connect,
    disconnect: state.disconnect,
    reconnect: state.reconnect,
  }))
}

/**
 * Hook to access message sending actions.
 */
export function useMessageActions() {
  return useDebateStore((state) => ({
    sendUserMessage: state.sendUserMessage,
    sendInterrupt: state.sendInterrupt,
  }))
}

/**
 * Hook to access user interaction state setters.
 */
export function useUserInteractionActions() {
  return useDebateStore((state) => ({
    setSelectedAgent: state.setSelectedAgent,
    setTrimCount: state.setTrimCount,
    setUserMessageDraft: state.setUserMessageDraft,
  }))
}

/**
 * Hook to access error management actions.
 */
export function useErrorActions() {
  return useDebateStore((state) => ({
    setError: state.setError,
    clearError: state.clearError,
  }))
}

/**
 * Hook to access store reset action.
 */
export function useResetStore() {
  return useDebateStore((state) => state.reset)
}

/**
 * Hook to access all store state (use sparingly to avoid unnecessary re-renders).
 */
export function useDebateStoreState() {
  return useDebateStore((state) => ({
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
export function useDebateStoreActions() {
  return useDebateStore((state) => ({
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
  return useDebateStore((state) => state.agentInputRequest)
}

/**
 * Hook to access agent input draft.
 */
export function useAgentInputDraft() {
  return useDebateStore((state) => state.agentInputDraft)
}

/**
 * Hook to access agent input actions.
 */
export function useAgentInputActions() {
  return useDebateStore((state) => ({
    sendAgentInputResponse: state.sendAgentInputResponse,
    setAgentInputDraft: state.setAgentInputDraft,
    clearAgentInputRequest: state.clearAgentInputRequest,
  }))
}
