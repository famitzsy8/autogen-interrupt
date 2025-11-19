import React, { useState, useEffect, useRef } from 'react'
import { ChatDisplay } from './components/ChatDisplay'
import { StateDisplay } from './components/StateDisplay'
import { TreeVisualization } from './components/TreeVisualization'
import AgentInputModal from './components/AgentInputModal'
import { ConfigForm } from './components/ConfigForm'
import { MessageSquare, FileText } from 'lucide-react'
import type { RunConfig } from './types'
import {
  useAgentInputActions,
  useAgentInputRequest,
  useAgentTeamNames,
  useAgentDetails,
  useParticipantNames,
  useConnectionActions,
  useConnectionState,
  useConversationTree,
  useCurrentBranchId,
  useIsChatDisplayVisible,
  useChatDisplayActions,
  useIsStateDisplayVisible,
  useStateDisplayActions,
} from './hooks/useStore'

function App(): React.ReactElement {
  const [isConfigured, setIsConfigured] = useState(false)
  const hasConnectedRef = useRef(false)
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8006/ws/agent'

  const { connect, sendConfig } = useConnectionActions()
  const connectionState = useConnectionState()
  const agentTeamNames = useAgentTeamNames()
  const agentDetails = useAgentDetails()
  const participantNames = useParticipantNames()
  const conversationTree = useConversationTree()
  const currentBranchId = useCurrentBranchId()
  const agentInputRequest = useAgentInputRequest()
  const isChatDisplayVisible = useIsChatDisplayVisible()
  const isStateDisplayVisible = useIsStateDisplayVisible()
  const { sendHumanInputResponse } = useAgentInputActions()
  const { setChatDisplayVisible } = useChatDisplayActions()
  const { setStateDisplayVisible } = useStateDisplayActions()

  const handleToggleChatDisplay = () => {
    setChatDisplayVisible(!isChatDisplayVisible)
  }

  const handleToggleStateDisplay = () => {
    setStateDisplayVisible(!isStateDisplayVisible)
  }

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
        agentDetails={agentDetails?.agents || null}
        participantNames={participantNames?.participant_names || null}
      />
    )
  }

  return (
    <div className="min-h-screen bg-dark-bg text-dark-text">
      <div className="relative h-screen w-full">
        {/* Tree visualization area (always full size) */}
        <div className="absolute inset-0">
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

          {/* Floating toggle button for chat display */}
          {!isChatDisplayVisible && (
            <button
              onClick={handleToggleChatDisplay}
              className="absolute top-4 right-4 p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg transition-colors z-10"
              aria-label="Show chat display"
              title="Show full messages"
            >
              <MessageSquare size={24} />
            </button>
          )}

          {/* Floating toggle button for state display */}
          {!isStateDisplayVisible && (
            <button
              onClick={handleToggleStateDisplay}
              className="absolute top-4 left-4 p-3 bg-purple-600 hover:bg-purple-700 text-white rounded-full shadow-lg transition-colors z-10"
              aria-label="Show state display"
              title="Show state context"
            >
              <FileText size={24} />
            </button>
          )}
        </div>

        {/* Chat display overlay (slides in from right) */}
        {isChatDisplayVisible && (
          <div className="fixed right-0 top-0 h-full w-[400px] bg-dark-bg border-l border-dark-border shadow-2xl z-40 transition-transform duration-300 flex flex-col">
            <ChatDisplay />
          </div>
        )}

        {/* State display overlay (slides in from left) */}
        {isStateDisplayVisible && (
          <div className="fixed left-0 top-0 h-full w-[400px] bg-dark-bg border-r border-dark-border shadow-2xl z-40 transition-transform duration-300 flex flex-col">
            <StateDisplay />
          </div>
        )}
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
