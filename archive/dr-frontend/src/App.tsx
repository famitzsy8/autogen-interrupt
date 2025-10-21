import React, { useEffect } from 'react'
import { ChatDisplay } from './components/ChatDisplay'
import { TreeVisualization } from './components/TreeVisualization'
import AgentInputModal from './components/AgentInputModal'
import {
  useAgentInputActions,
  useAgentInputRequest,
  useConnectionActions,
  useConnectionState,
  useConversationTree,
  useCurrentBranchId,
} from './hooks/useResearchStore'

function App(): React.ReactElement {
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws/research'
  const { connect, disconnect } = useConnectionActions()
  const connectionState = useConnectionState()
  const conversationTree = useConversationTree()
  const currentBranchId = useCurrentBranchId()
  const agentInputRequest = useAgentInputRequest()
  const { sendAgentInputResponse } = useAgentInputActions()

  // Connect to WebSocket on mount
  useEffect(() => {
    connect(wsUrl)

    // Cleanup on unmount
    return () => {
      disconnect()
    }
  }, [wsUrl, connect, disconnect])

  return (
    <div className="min-h-screen bg-dark-bg text-dark-text">
      <div className="flex h-screen">
        {/* Tree visualization area (70% width) */}
        <div className="flex-[0_0_70%] border-r border-dark-border">
          <TreeVisualization
            treeData={conversationTree}
            currentBranchId={currentBranchId}
          />
        </div>

        {/* Chat display area (30% width) */}
        <div className="flex-[0_0_30%] flex flex-col">
          <ChatDisplay />
        </div>
      </div>

      {/* Connection status indicator */}
      <div className="fixed bottom-4 right-4 z-50">
        <div
          className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg shadow-lg text-xs ${
            connectionState === 'connected'
              ? 'bg-green-900 text-green-300'
              : connectionState === 'connecting' || connectionState === 'reconnecting'
                ? 'bg-yellow-900 text-yellow-300'
                : 'bg-red-900 text-red-300'
          }`}
        >
          <div
            className={`w-2 h-2 rounded-full ${
              connectionState === 'connected'
                ? 'bg-green-400 animate-pulse'
                : connectionState === 'connecting' || connectionState === 'reconnecting'
                  ? 'bg-yellow-400 animate-pulse'
                  : 'bg-red-400'
            }`}
          />
          <span className="font-medium">{connectionState}</span>
        </div>
      </div>

      {/* Agent Input Modal */}
      {agentInputRequest && (
        <AgentInputModal
          request={agentInputRequest}
          onSubmit={(userInput) => {
            sendAgentInputResponse(agentInputRequest.request_id, userInput)
          }}
          onCancel={() => {
            // Send empty string when user cancels
            sendAgentInputResponse(agentInputRequest.request_id, 'continue')
          }}
        />
      )}
    </div>
  )
}

export default App
