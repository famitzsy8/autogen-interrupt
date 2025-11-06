/**
 * Hooks for using the agent team store.
 * 
 * These hooks are the interface to access the Zustand store
 */

// TODO: Here we have to think about how to provide the interface
// to access the agent team names ---> UPDATE: did that already, with useAgentTeamNames


import {useStore} from '../store/store'

import type {
    AgentMessage,
    AppError,
    ConnectionState,
    StreamState,
    TreeNode
} from '../types'

export function useConnectionState(): ConnectionState {
    return useStore((state) => state.connectionState)
}

export function useIsConnected(): boolean {
    return useStore((state) => state.connectionState === 'connected')
}

/**
 * Hook to access all conversation messages.
 */
export function useMessages(): AgentMessage[] {
    return useStore((state) => state.messages)
}

/**
 * Hook to access the conversation tree.
 */
export function useConversationTree(): TreeNode | null {
    return useStore((state) => state.conversationTree)
}

/**
 * Hook to access the current branch ID.
 */
export function useCurrentBranchId(): string {
    return useStore((state) => state.currentBranchId)
}

/**
 * Hook to access the active node ID.
 */
export function useActiveNodeId(): string | null {
    return useStore((state) => state.activeNodeId)
}

/**
 * Hook to access stream state.
 */
export function useStreamState(): StreamState {
    return useStore((state) => state.streamState)
}

/**
 * Hook to check if stream is interrupted.
 */
export function useIsInterrupted(): boolean {
    return useStore((state) => state.isInterrupted)
}



/**
 * Hook to check if stream is actively streaming.
 */
export function useIsStreaming(): boolean {
    return useStore((state) => state.streamState === 'streaming')
  }
  
  /**
   * Hook to access selected agent for user messages.
   */
  export function useSelectedAgent(): string | null {
    return useStore((state) => state.selectedAgent)
  }
  
  /**
   * Hook to access trim count.
   */
  export function useTrimCount(): number {
    return useStore((state) => state.trimCount)
  }
  
  /**
   * Hook to access user message draft.
   */
  export function useUserMessageDraft(): string {
    return useStore((state) => state.userMessageDraft)
  }
  
  /**
   * Hook to access current error state.
   */
  export function useError(): AppError | null {
    return useStore((state) => state.error)
  }
  
  /**
   * Hook to access WebSocket connection actions.
   */
  export function useConnectionActions() {
    return useStore((state) => ({
      connect: state.connect,
      sendConfig: state.sendConfig,
      disconnect: state.disconnect,
      reconnect: state.reconnect,
    }))
  }

  /**
   * Hook to access the agent names in the team
   */
  export function useAgentTeamNames() {
    return useStore((state) => state.agent_names)
  }
  
  /**
   * Hook to access message sending actions.
   */
  export function useMessageActions() {
    return useStore((state) => ({
      sendUserMessage: state.sendUserMessage,
      sendInterrupt: state.sendInterrupt,
    }))
  }
  
  /**
   * Hook to access user interaction state setters.
   */
  export function useUserInteractionActions() {
    return useStore((state) => ({
      setSelectedAgent: state.setSelectedAgent,
      setTrimCount: state.setTrimCount,
      setUserMessageDraft: state.setUserMessageDraft,
    }))
  }
  
  /**
   * Hook to access error management actions.
   */
  export function useErrorActions() {
    return useStore((state) => ({
      setError: state.setError,
      clearError: state.clearError,
    }))
  }
  
  /**
   * Hook to access store reset action.
   */
  export function useResetStore() {
    return useStore((state) => state.reset)
  }
  
  /**
   * Hook to access all store state (use sparingly to avoid unnecessary re-renders).
   */
  export function useStoreState() {
    return useStore((state) => ({
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
  export function useStoreActions() {
    return useStore((state) => ({
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
    return useStore((state) => state.agentInputRequest)
  }
  
  /**
   * Hook to access agent input draft.
   */
  export function useHumanInputDraft() {
    return useStore((state) => state.humanInputDraft)
  }

  /**
   * Hook to access agent input draft (alias for useHumanInputDraft).
   */
  export function useAgentInputDraft() {
    return useStore((state) => state.humanInputDraft)
  }
  
  /**
   * Hook to access agent input actions.
   */
  export function useAgentInputActions() {
    return useStore((state) => ({
      sendHumanInputResponse: state.sendHumanInputResponse,
      setHumanInputDraft: state.setHumanInputDraft,
      clearAgentInputRequest: state.clearAgentInputRequest,
    }))
  }

  /**
   * Hook to access tool calls by node ID.
   */
  export function useToolCallsByNodeId(): Record<string, import('../types').ToolCall> {
    return useStore((state) => state.toolCallsByNodeId)
  }
  
  /**
   * Hook to access tool executions by node ID.
   */
  export function useToolExecutionsByNodeId(): Record<string, import('../types').ToolExecution> {
    return useStore((state) => state.toolExecutionsByNodeId)
  }
  