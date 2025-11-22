import React, { useState, useEffect, useRef } from 'react'
import { FloatingInputPanel } from './components/FloatingInputPanel'
import { InterruptButton } from './components/InterruptButton'
import { StateDisplay } from './components/StateDisplay'
import { TreeVisualization } from './components/TreeVisualization'
import AgentInputModal from './components/AgentInputModal'
import { ConfigForm } from './components/ConfigForm'
import { ErrorBoundary } from './components/ErrorBoundary'
import { FileText } from 'lucide-react'
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
  useIsStreaming,
  useMessageActions,
  useUserInteractionActions,
  useIsStateDisplayVisible,
  useStateDisplayActions,
  useIsInterrupted,
  useTrimCount,
  useEdgeInterrupt,
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
  const isStreaming = useIsStreaming()
  const { sendInterrupt, sendUserMessage } = useMessageActions()
  const { setTrimCount } = useUserInteractionActions()
  const isStateDisplayVisible = useIsStateDisplayVisible()
  const { sendHumanInputResponse } = useAgentInputActions()
  const { setStateDisplayVisible } = useStateDisplayActions()
  const isInterrupted = useIsInterrupted()
  const trimCount = useTrimCount()
  const edgeInterrupt = useEdgeInterrupt()
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)


  const handleToggleStateDisplay = () => {
    setStateDisplayVisible(!isStateDisplayVisible)
  }

  const handleInterrupt = () => {
    sendInterrupt()
    setTrimCount(0)
  }

  const handleSendMessage = (content: string, targetAgent: string, trimCount: number) => {
    sendUserMessage(content, targetAgent, trimCount)
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
    <ErrorBoundary>
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



            {/* Top right controls */}
            <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
              {/* Interrupt Button */}
              <InterruptButton onInterrupt={handleInterrupt} isStreaming={isStreaming} />

              {/* Floating toggle button for state display */}
              {!isStateDisplayVisible && (
                <button
                  onClick={handleToggleStateDisplay}
                  className="p-3 bg-dark-surface hover:bg-dark-accent text-dark-text rounded-full shadow-lg transition-colors"
                  aria-label="Show state display"
                  title="Show state history"
                >
                  <FileText size={24} />
                </button>
              )}
            </div>
          </div>

          {/* Floating Input Panel (replaces ControlBar) - Only show when no edge interrupt is active */}
          {!edgeInterrupt && (
            <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50">
              <FloatingInputPanel
                onSendMessage={handleSendMessage}
                isInterrupted={isInterrupted}
                selectedAgent={selectedAgent}
                onSelectAgent={setSelectedAgent}
                trimCount={trimCount}
              />
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
            className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg shadow-lg text-xs ${connectionState === 'connected'
              ? 'bg-green-900 text-green-300'
              : connectionState === 'connecting' || connectionState === 'reconnecting'
                ? 'bg-yellow-900 text-yellow-300'
                : 'bg-red-900 text-red-300'
              }`}
          >
            <div
              className={`w-2 h-2 rounded-full ${connectionState === 'connected'
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
    </ErrorBoundary>
  )
}

export default App
