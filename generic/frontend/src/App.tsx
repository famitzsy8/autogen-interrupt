import React, { useState, useEffect, useRef } from 'react'
import { ChatDisplay } from './components/ChatDisplay'
import { TreeVisualization } from './components/TreeVisualization'
import AgentInputModal from './components/AgentInputModal'
import { ConfigForm } from './components/ConfigForm'
import type { RunConfig } from './types'
import {
  useAgentInputActions,
  useAgentInputRequest,
  useAgentTeamNames,
  useConnectionActions,
  useConnectionState,
  useConversationTree,
  useCurrentBranchId,
} from './hooks/useStore'

function App(): React.ReactElement {
  const [isConfigured, setIsConfigured] = useState(false)
  const hasConnectedRef = useRef(false)
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws/agent'

  const { connect, sendConfig, disconnect } = useConnectionActions()
  const connectionState = useConnectionState()
  const agentTeamNames = useAgentTeamNames()
  const conversationTree = useConversationTree()
  const currentBranchId = useCurrentBranchId()
  const agentInputRequest = useAgentInputRequest()
  const { sendHumanInputResponse } = useAgentInputActions()

  // Connect to WebSocket on mount (only once)
  useEffect(() => {
    if (!hasConnectedRef.current && !isConfigured) {
      hasConnectedRef.current = true
      connect(wsUrl)
    }
    // No cleanup function - let WebSocket stay open across Strict Mode remounts
  }, [])

  const handleConfigSubmit = async (config: RunConfig) => {
    try {
      console.log('=== Config submitted, sending to backend ===')
      sendConfig(config)
      setIsConfigured(true)
    } catch (error) {
      console.error('Failed to send config:', error)
    }
  }

  // Show config form after receiving agent team names but before starting
  if (!isConfigured) {
    return (
      <ConfigForm
        onSubmit={handleConfigSubmit}
        isLoading={connectionState === 'connecting'}
        agentTeamNames={agentTeamNames?.agent_team_names || null}
      />
    )
  }

  return (
    <div className="min-h-screen bg-dark-bg text-dark-text">
      <div className="flex h-screen">
        {/* Tree visualization area (70% width) */}
        <div className="flex-[0_0_70%] border-r border-dark-border relative">
          <TreeVisualization
            treeData={conversationTree}
            currentBranchId={currentBranchId}
          />

          {/* Agent Input Modal - positioned in tree area */}
          {agentInputRequest && (
            <AgentInputModal
              request={agentInputRequest}
              onSubmit={(userInput) => {
                sendHumanInputResponse(agentInputRequest.request_id, userInput)
              }}
              onCancel={() => {
                // Send 'continue' when user cancels
                sendHumanInputResponse(agentInputRequest.request_id, 'continue')
              }}
            />
          )}
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
    </div>
  )
}

export default App
