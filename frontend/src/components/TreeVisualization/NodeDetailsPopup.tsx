/**
 * NodeDetailsPopup displays detailed information about a tree node.
 *
 * Features:
 * - Modal overlay with backdrop
 * - Header with agent display name, summary, and timestamp
 * - Tab navigation: Message, Run State, Tool Effects, Handoff
 * - Tabs are disabled if data is missing
 * - Scrollable content area for each tab
 * - Close button with X icon
 */

import React, { useState } from 'react'
import { X, AlertTriangle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import type { TreeNode, StateUpdate, ToolCall, ToolExecution } from '../../types'
import { useStore } from '../../store/store'
import { AnalysisScoreDisplay } from './AnalysisScoreDisplay'
import { AgentBadge } from '../AgentBadge'

interface NodeDetailsPopupProps {
  node: TreeNode
  stateUpdate?: StateUpdate
  toolCall?: ToolCall
  toolExecution?: ToolExecution
  onClose: () => void
}

type TabName = 'message' | 'runState' | 'toolEffects'

interface Tab {
  id: TabName
  label: string
  isEnabled: boolean
}

// Component to display tool arguments
function ToolArgumentsList({ tool }: { tool: { id: string; name: string; arguments: string } }): React.ReactElement {
  try {
    const args = JSON.parse(tool.arguments)
    return (
      <div className="bg-black bg-opacity-30 p-3 rounded text-xs font-mono">
        {Object.entries(args).map(([key, value]) => (
          <div key={key} className="mb-1">
            <span className="text-dark-accent">{key}:</span>{' '}
            <span className="text-gray-300">
              {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
            </span>
          </div>
        ))}
      </div>
    )
  } catch {
    // If JSON parsing fails, show raw arguments
    return (
      <pre className="bg-black bg-opacity-30 p-3 rounded text-xs font-mono text-gray-300 overflow-x-auto">
        {tool.arguments}
      </pre>
    )
  }
}

export function NodeDetailsPopup({
  node,
  stateUpdate,
  toolCall,
  toolExecution,
  onClose,
}: NodeDetailsPopupProps): React.ReactElement {
  const [activeTab, setActiveTab] = useState<TabName>('message')

  // Get analysis data from store
  const analysisComponents = useStore((state) => state.analysisComponents)
  const analysisScores = useStore((state) => state.analysisScores)
  const triggeredNodes = useStore((state) => state.triggeredNodes)

  const nodeScores = analysisScores.get(node.id)
  const isTriggered = triggeredNodes.has(node.id)

  // Define tabs with enabled state based on data availability
  const tabs: Tab[] = [
    {
      id: 'message',
      label: 'Message',
      isEnabled: Boolean(node.message),
    },
    {
      id: 'runState',
      label: 'Run State',
      isEnabled: Boolean(stateUpdate),
    },
    {
      id: 'toolEffects',
      label: 'Actions',
      isEnabled: Boolean(toolCall || toolExecution),
    },
  ]

  // Handle backdrop click to close
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>): void => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  // Handle tab change - only allow enabled tabs
  const handleTabChange = (tabId: TabName): void => {
    const tab = tabs.find((t) => t.id === tabId)
    if (tab?.isEnabled) {
      setActiveTab(tabId)
    }
  }

  // Render tab content based on active tab
  const renderTabContent = (): React.ReactElement => {
    switch (activeTab) {
      case 'message':
        return (
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-dark-accent mb-2">Message Content</h3>
              {node.node_type === 'tool_call' && toolCall ? (
                <div className="space-y-3">
                  {toolCall.tools.map((tool) => (
                    <div key={tool.id} className="space-y-2">
                      <h4 className="font-semibold text-dark-text">{tool.name}</h4>
                      <ToolArgumentsList tool={tool} />
                    </div>
                  ))}
                </div>
              ) : node.message ? (
                <div className="text-sm text-dark-text leading-relaxed whitespace-pre-wrap font-mono">
                  <ReactMarkdown>{node.message}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-gray-500 italic text-sm">(no message content)</p>
              )}
            </div>

            {/* Analysis Scores Section */}
            {nodeScores && (
              <div className="pt-4 border-t border-dark-border">
                <div className="flex items-center justify-between mb-3">
                  {isTriggered && (
                    <span className="flex items-center gap-1 px-3 py-1 bg-red-900/30 text-red-400 border border-red-800 rounded-full text-xs font-medium">
                      <AlertTriangle size={12} />
                      Triggered Feedback
                    </span>
                  )}
                </div>
                <AnalysisScoreDisplay
                  components={analysisComponents}
                  scores={nodeScores.scores}
                  triggerThreshold={8}
                />
              </div>
            )}

            {!nodeScores && analysisComponents.length > 0 && (
              <div className="pt-4 border-t border-dark-border">
                <p className="text-gray-500 italic text-sm">
                  Analysis scores not yet available for this node
                </p>
              </div>
            )}
          </div>
        )

      case 'runState':
        return (
          <div className="space-y-4">
            {/* State of Run Section */}
            <div>
              <h3 className="text-sm font-semibold text-dark-accent mb-2">State of Run</h3>
              {stateUpdate?.state_of_run ? (
                <div className="text-sm text-dark-text markdown-content">
                  <ReactMarkdown>{stateUpdate.state_of_run}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-gray-500 italic text-sm">(no state data)</p>
              )}
            </div>

            {/* Tool Call Facts Section */}
            <div className="pt-4 border-t border-dark-border">
              <h3 className="text-sm font-semibold text-dark-accent mb-2">Tool Call Facts</h3>
              {stateUpdate?.tool_call_facts ? (
                <div className="text-sm text-dark-text markdown-content">
                  <ReactMarkdown>{stateUpdate.tool_call_facts}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-gray-500 italic text-sm">(no tool call facts)</p>
              )}
            </div>
          </div>
        )

      case 'toolEffects':
        return (
          <div className="space-y-6">
            {/* Tool Calls Section */}
            {toolCall && (
              <div>
                <h3 className="text-sm font-semibold text-dark-accent mb-3">Actions Requested</h3>
                <div className="space-y-3">
                  {toolCall.tools.map((tool) => (
                    <ToolCallItem key={tool.id} tool={tool} />
                  ))}
                </div>
              </div>
            )}

            {/* Tool Execution Results Section */}
            {toolExecution && (
              <div className={toolCall ? 'pt-6 border-t border-dark-border' : ''}>
                <h3 className="text-sm font-semibold text-dark-accent mb-3">Action Results</h3>
                <div className="space-y-3">
                  {toolExecution.results.map((result) => (
                    <ToolResultItem key={result.tool_call_id} result={result} />
                  ))}
                </div>
              </div>
            )}

            {!toolCall && !toolExecution && (
              <p className="text-gray-500 italic text-sm">(no actions recorded)</p>
            )}
          </div>
        )

      default:
        return <div className="text-gray-500 italic text-sm">Unknown tab</div>
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60"
      onClick={handleBackdropClick}
    >
      {/* Modal Container */}
      <div className="bg-dark-bg border border-dark-border rounded-lg shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="border-b border-dark-border p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="mb-2">
                <AgentBadge
                  agentName={node.agent_name}
                  displayName={node.display_name}
                  size="lg"
                />
              </div>
              {node.summary && (
                <p className="text-sm text-gray-400">{node.summary}</p>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-200 hover:bg-dark-hover rounded transition-colors flex-shrink-0"
              aria-label="Close popup"
              title="Close"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-dark-border px-5">
          <div className="flex gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                disabled={!tab.isEnabled}
                className={`px-4 py-3 text-sm font-medium transition-colors relative ${activeTab === tab.id
                  ? 'text-dark-accent'
                  : tab.isEnabled
                    ? 'text-gray-400 hover:text-gray-200'
                    : 'text-gray-600 cursor-not-allowed'
                  } ${!tab.isEnabled ? 'opacity-50' : ''}`}
              >
                {tab.label}
                {activeTab === tab.id && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-dark-accent"></div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {renderTabContent()}
        </div>
      </div>
    </div>
  )
}

function ToolCallItem({ tool }: { tool: { id: string; name: string; arguments: string } }) {
  const [showDetails, setShowDetails] = useState(false)

  return (
    <div className="border border-dark-border rounded-lg bg-dark-hover overflow-hidden">
      <div
        className="p-3 flex items-center justify-between cursor-pointer hover:bg-dark-surface transition-colors"
        onClick={() => setShowDetails(!showDetails)}
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-dark-text">{tool.name}</span>
        </div>
        <span className="text-xs text-dark-accent hover:underline">
          {showDetails ? 'Hide Details' : 'Show Details'}
        </span>
      </div>

      {showDetails && (
        <div className="p-3 border-t border-dark-border bg-dark-bg">
          <div className="text-xs text-gray-400 mb-1">Arguments:</div>
          <pre className="text-xs font-mono text-gray-300 bg-black bg-opacity-30 p-2 rounded overflow-x-auto">
            {tool.arguments}
          </pre>
          <div className="text-xs text-gray-600 mt-2">ID: {tool.id}</div>
        </div>
      )}
    </div>
  )
}

function ToolResultItem({ result }: { result: { tool_call_id: string; tool_name: string; result: string | null; success: boolean } }) {
  const [showDetails, setShowDetails] = useState(false)

  return (
    <div className="border border-dark-border rounded-lg bg-dark-hover overflow-hidden">
      <div
        className="p-3 flex items-center justify-between cursor-pointer hover:bg-dark-surface transition-colors"
        onClick={() => setShowDetails(!showDetails)}
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-dark-text">{result.tool_name}</span>
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${result.success
              ? 'bg-green-900/50 text-green-400 border border-green-800'
              : 'bg-red-900/50 text-red-400 border border-red-800'
              }`}
          >
            {result.success ? 'Success' : 'Failed'}
          </span>
        </div>
        <span className="text-xs text-dark-accent hover:underline">
          {showDetails ? 'Hide Details' : 'Show Details'}
        </span>
      </div>

      {showDetails && result.result && (
        <div className="p-3 border-t border-dark-border bg-dark-bg">
          <div className="text-xs text-gray-400 mb-1">Result Output:</div>
          <pre className="text-xs font-mono text-gray-300 bg-black bg-opacity-30 p-2 rounded overflow-x-auto max-h-64">
            {result.result}
          </pre>
        </div>
      )}
    </div>
  )
}
