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
    StateUpdate,
    StreamState,
    ToolCall,
    ToolExecution,
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
   * Hook to access the participant names (individual agents)
   */
  export function useParticipantNames() {
    return useStore((state) => state.participant_names)
  }

  /**
   * Hook to access the agent details (names and descriptions)
   */
  export function useAgentDetails() {
    return useStore((state) => state.agent_details)
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
   * Returns a map of node_id -> ToolCall message.
   * Used to look up tool call details for a given node.
   */
  export function useToolCallsByNodeId(): Record<string, ToolCall> {
    return useStore((state) => state.toolCallsByNodeId)
  }

  /**
   * Hook to access tool executions by node ID.
   * Returns a map of node_id -> ToolExecution message.
   * Used to look up tool execution results for a given node.
   * Note: ToolCall and ToolExecution may share the same node_id.
   */
  export function useToolExecutionsByNodeId(): Record<string, ToolExecution> {
    return useStore((state) => state.toolExecutionsByNodeId)
  }

  /**
   * Hook to access chat display visibility state.
   */
  export function useIsChatDisplayVisible(): boolean {
    return useStore((state) => state.isChatDisplayVisible)
  }

  /**
   * Hook to access the selected node ID for chat.
   */
export function useSelectedNodeIdForChat(): string | null {
    return useStore((state) => state.selectedNodeIdForChat)
}

export function useChatFocusTarget() {
  return useStore((state) => state.chatFocusTarget)
}

/**
 * Hook to access chat display actions.
 */
export function useChatDisplayActions() {
    return useStore((state) => ({
      setChatDisplayVisible: state.setChatDisplayVisible,
      setSelectedNodeIdForChat: state.setSelectedNodeIdForChat,
      setChatFocusTarget: state.setChatFocusTarget,
    }))
  }

  /**
   * Hook to access current state update.
   */
  export function useCurrentState(): StateUpdate | null {
    return useStore((state) => state.currentState)
  }

  /**
   * Hook to access all state updates received from the backend.
   * Returns an ordered list of all StateUpdate messages accumulated during the session.
   * StateUpdates are sparse (not emitted for every message).
   * Used for temporal lookup when populating Run State tab.
   */
  export function useAllStateUpdates(): StateUpdate[] {
    return useStore((state) => state.stateUpdates)
  }

  /**
   * Hook to check if state display is visible.
   */
  export function useIsStateDisplayVisible(): boolean {
    return useStore((state) => state.isStateDisplayVisible)
  }

  /**
   * Hook to access state display actions.
   */
  export function useStateDisplayActions() {
    return useStore((state) => ({
      setStateDisplayVisible: state.setStateDisplayVisible,
    }))
  }

  /**
   * Hook to access edge interrupt state.
   */
  export function useEdgeInterrupt(): { targetNodeId: string; position: { x: number; y: number }; trimCount: number } | null {
    return useStore((state) => state.edgeInterrupt)
  }

  /**
   * Hook to access edge interrupt actions.
   */
  export function useEdgeInterruptActions(): {
    setEdgeInterrupt: (targetNodeId: string, position: { x: number; y: number }, trimCount: number) => void
    clearEdgeInterrupt: () => void
  } {
    return useStore((state) => ({
      setEdgeInterrupt: state.setEdgeInterrupt,
      clearEdgeInterrupt: state.clearEdgeInterrupt,
    }))
  }

  /**
   * Hook to access analysis components.
   */
  export function useAnalysisComponents() {
    return useStore((state) => state.analysisComponents)
  }

  /**
   * Hook to access analysis scores by node ID.
   */
  export function useAnalysisScores() {
    return useStore((state) => state.analysisScores)
  }

  /**
   * Hook to access triggered nodes set.
   */
  export function useTriggeredNodes() {
    return useStore((state) => state.triggeredNodes)
  }

  /**
   * Hook to access analysis actions.
   */
  export function useAnalysisActions() {
    return useStore((state) => ({
      setAnalysisComponents: state.setAnalysisComponents,
      addAnalysisScore: state.addAnalysisScore,
      markNodeTriggered: state.markNodeTriggered,
      clearAnalysisData: state.clearAnalysisData,
    }))
  }

  /**
   * Hook to access generated components for review.
   */
  export function useGeneratedComponents() {
    return useStore((state) => state.generatedComponents)
  }

  /**
   * Hook to check if components are being generated.
   */
  export function useIsGeneratingComponents(): boolean {
    return useStore((state) => state.isGeneratingComponents)
  }

  /**
   * Hook to access component generation actions.
   */
  export function useComponentGenerationActions() {
    return useStore((state) => ({
      sendComponentGenerationRequest: state.sendComponentGenerationRequest,
      sendRunStartConfirmed: state.sendRunStartConfirmed,
    }))
  }
