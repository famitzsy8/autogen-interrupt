import React, { useState, useEffect, useRef } from 'react'
import { FloatingInputPanel } from './components/FloatingInputPanel'
import { InterruptButton } from './components/InterruptButton'
import { TerminateButton } from './components/TerminateButton'
import { StateDisplay } from './components/StateDisplay'
import { TreeVisualization } from './components/TreeVisualization'
import AgentInputModal, { AgentInputMinimizedTab } from './components/AgentInputModal'
import TerminationModal from './components/TerminationModal'
import { ConfigForm } from './components/ConfigForm'
import { ErrorBoundary } from './components/ErrorBoundary'
import { ChevronLeft, Sun, Moon } from 'lucide-react'
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
  useIsInterrupted,
  useTrimCount,
  useEdgeInterrupt,
  useEdgeInterruptActions,
  useAnalysisActions,
} from './hooks/useStore'
import type { TreeNode } from './types'

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
  const isInterrupted = useIsInterrupted()
  const trimCount = useTrimCount()
  const edgeInterrupt = useEdgeInterrupt()
  const { clearEdgeInterrupt } = useEdgeInterruptActions()
  const { markNodeUserInterrupted } = useAnalysisActions()
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const [isDarkMode, setIsDarkMode] = useState(false)
  const [isInputPanelMinimized, setIsInputPanelMinimized] = useState(false)
  const [isAgentInputMinimized, setIsAgentInputMinimized] = useState(false)

  // Find the last active node in the tree (deepest node in active branch)
  const findLastActiveNode = (node: TreeNode): TreeNode | null => {
    if (!node.is_active) return null

    // Check children for deeper active nodes
    if (node.children && node.children.length > 0) {
      for (const child of node.children) {
        const deeperNode = findLastActiveNode(child)
        if (deeperNode) return deeperNode
      }
    }

    // This node is active and has no active children, so it's the last
    return node
  }

  const handleInterrupt = () => {
    sendInterrupt()
    setTrimCount(0)

    // Mark the last active node as user-interrupted
    if (conversationTree) {
      const lastNode = findLastActiveNode(conversationTree)
      if (lastNode) {
        markNodeUserInterrupted(lastNode.id)
      }
    }
  }

  const handleSendMessage = (content: string, targetAgent: string, trimCount: number) => {
    sendUserMessage(content, targetAgent, trimCount)
    // Clear edge interrupt state after sending message
    if (edgeInterrupt) {
      clearEdgeInterrupt()
    }
  }

  // Connect to WebSocket on mount (only once)
  useEffect(() => {
    if (!hasConnectedRef.current && !isConfigured) {
      hasConnectedRef.current = true
      connect(wsUrl)
    }
    // No cleanup function - let WebSocket stay open across Strict Mode remounts
  }, [])

  // Reset minimized state when interrupt happens so panel shows again
  useEffect(() => {
    if (isInterrupted) {
      setIsInputPanelMinimized(false)
    }
  }, [isInterrupted])

  // Reset agent input minimized state when new request comes in
  useEffect(() => {
    if (agentInputRequest) {
      setIsAgentInputMinimized(false)
    }
  }, [agentInputRequest])

  // Toggle dark mode class on document
  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDarkMode)
  }, [isDarkMode])

  const handleConfigSubmit = async (config: RunConfig) => {
    try {
      sendConfig(config)
      setIsConfigured(true)
    } catch (error) {
      // Handle error silently
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




            {/* Top right controls */}
            <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
              {/* Theme Toggle */}
              <button
                onClick={() => setIsDarkMode(!isDarkMode)}
                className="p-2 rounded-lg bg-dark-surface border border-dark-border hover:bg-dark-hover transition-colors"
                title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
              </button>

              {/* Interrupt Button */}
              <InterruptButton onInterrupt={handleInterrupt} isStreaming={isStreaming} />

              {/* Terminate Button - ends run and shows final state */}
              <TerminateButton />
            </div>
          </div>

          {/* Floating Input Panel - slides in from right side for both button and edge interrupts */}
          {(isInterrupted || edgeInterrupt) && !agentInputRequest && (
            <>
              {/* Expanded panel */}
              <div
                className={`fixed right-0 top-1/2 -translate-y-1/2 z-50 transition-transform duration-300 ease-in-out ${isInputPanelMinimized ? 'translate-x-full' : 'translate-x-0'
                  }`}
              >
                <FloatingInputPanel
                  onSendMessage={handleSendMessage}
                  isInterrupted={isInterrupted || !!edgeInterrupt}
                  selectedAgent={selectedAgent}
                  onSelectAgent={setSelectedAgent}
                  trimCount={edgeInterrupt?.trimCount ?? trimCount}
                  onMinimize={() => setIsInputPanelMinimized(true)}
                  className="rounded-l-lg rounded-r-none border-r-0"
                />
              </div>

              {/* Collapsed tab button - only show when minimized */}
              {isInputPanelMinimized && (
                <button
                  onClick={() => setIsInputPanelMinimized(false)}
                  className="fixed right-0 top-1/2 -translate-y-1/2 z-50 bg-dark-accent hover:bg-dark-accent/80 text-white px-3 py-2 rounded-l-lg shadow-lg transition-all duration-200 flex items-center gap-2 text-sm font-medium"
                  title="Open message panel"
                >
                  <ChevronLeft size={18} />
                  <span>Complete your interruption!</span>
                </button>
              )}
            </>
          )}

          {/* Agent Input Modal - slides in from right side */}
          {agentInputRequest && (
            <>
              <AgentInputModal
                request={agentInputRequest}
                onSubmit={(userInput) => {
                  sendHumanInputResponse(agentInputRequest.request_id, userInput)
                }}
                onCancel={() => {
                  // Send 'continue' when user cancels
                  sendHumanInputResponse(agentInputRequest.request_id, 'continue')
                }}
                isMinimized={isAgentInputMinimized}
                onMinimize={() => setIsAgentInputMinimized(true)}
              />

              {/* Collapsed tab button for agent input - only show when minimized */}
              {isAgentInputMinimized && (
                <AgentInputMinimizedTab
                  onClick={() => setIsAgentInputMinimized(false)}
                  hasFeedbackContext={!!agentInputRequest.feedback_context}
                />
              )}
            </>
          )}

          {/* State display overlay (slides in from left) */}
          {isStateDisplayVisible && (
            <div className="fixed left-0 top-0 h-full w-[400px] bg-dark-bg border-r border-dark-border shadow-2xl z-40 transition-transform duration-300 flex flex-col">
              <StateDisplay />
            </div>
          )}
        </div>

        {/* Termination Modal - displays when run is terminated by user */}
        <TerminationModal />
      </div>
    </ErrorBoundary>
  )
}

export default App
