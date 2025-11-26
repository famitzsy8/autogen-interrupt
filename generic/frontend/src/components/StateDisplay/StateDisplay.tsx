/**
 * StateDisplay shows the current state of the GroupChatManager's 3-state model.
 *
 * Features:
 * - Displays state_of_run (research progress and next steps)
 * - Displays tool_call_facts (accumulated facts from tool executions)
 * - Displays handoff_context (agent selection rules and guidelines)
 * - Collapsible sections for each state
 * - Markdown rendering for state content
 * - Auto-updates when new state snapshots are created
 */

import React from 'react'
import { X, FileText, ChevronDown, ChevronRight } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useCurrentState, useStateDisplayActions } from '../../hooks/useStore'
import './StateDisplay.css'

export function StateDisplay(): React.ReactElement {
  const currentState = useCurrentState()
  const { setStateDisplayVisible } = useStateDisplayActions()

  // State for tracking which sections are expanded (all collapsed by default)
  const [expandedSections, setExpandedSections] = React.useState({
    stateOfRun: false,
    toolCallFacts: false,
    handoffContext: false,
  })


  const handleCloseStateDisplay = (): void => {
    setStateDisplayVisible(false)
  }

  const toggleSection = (section: keyof typeof expandedSections): void => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  return (
    <div className="flex flex-col h-full bg-dark-bg">
      {/* Header */}
      <div className="border-b border-dark-border p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1">
            <FileText size={20} className="text-dark-text" />
            <h2 className="text-xl font-semibold text-dark-text">State Context</h2>
          </div>
          <button
            onClick={handleCloseStateDisplay}
            className="p-2 text-gray-400 hover:text-gray-200 hover:bg-dark-hover rounded transition-colors"
            aria-label="Close state display"
            title="Hide state display"
          >
            <X size={20} />
          </button>
        </div>
        {currentState && (
          <div className="mt-1 text-xs text-gray-500">
            Last updated: Message #{currentState.message_index}
          </div>
        )}
      </div>

      {/* State content */}
      <div className="flex-1 overflow-y-auto p-4">
        {!currentState ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 text-sm">No state updates yet. Waiting for conversation to start...</p>
          </div>
        ) : (
          <div className="space-y-3">
            {/* State of Run */}
            <div className="border border-dark-border rounded-lg bg-dark-surface">
              <button
                onClick={() => toggleSection('stateOfRun')}
                className="w-full flex items-center justify-between p-4 hover:bg-dark-hover transition-colors"
              >
                {expandedSections.stateOfRun ? (
                  <ChevronDown size={18} className="text-gray-400" />
                ) : (
                  <ChevronRight size={18} className="text-gray-400" />
                )}
              </button>
              {expandedSections.stateOfRun && (
                <div className="px-4 pb-4 text-sm text-dark-text markdown-content">
                  {currentState.state_of_run ? (
                    <ReactMarkdown>{currentState.state_of_run}</ReactMarkdown>
                  ) : (
                    <p className="text-gray-500 italic">(empty)</p>
                  )}
                </div>
              )}
            </div>

            {/* Tool Call Facts */}
            <div className="border border-dark-border rounded-lg bg-dark-surface">
              <button
                onClick={() => toggleSection('toolCallFacts')}
                className="w-full flex items-center justify-between p-4 hover:bg-dark-hover transition-colors"
              >
                {expandedSections.toolCallFacts ? (
                  <ChevronDown size={18} className="text-gray-400" />
                ) : (
                  <ChevronRight size={18} className="text-gray-400" />
                )}
              </button>
              {expandedSections.toolCallFacts && (
                <div className="px-4 pb-4 text-sm text-dark-text markdown-content">
                  {currentState.tool_call_facts ? (
                    <ReactMarkdown>{currentState.tool_call_facts}</ReactMarkdown>
                  ) : (
                    <p className="text-gray-500 italic">(empty)</p>
                  )}
                </div>
              )}
            </div>

            {/* Handoff Context */}
            <div className="border border-dark-border rounded-lg bg-dark-surface">
              <button
                onClick={() => toggleSection('handoffContext')}
                className="w-full flex items-center justify-between p-4 hover:bg-dark-hover transition-colors"
              >
                <h3 className="text-sm font-semibold text-dark-accent flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                  Handoff Context
                </h3>
                {expandedSections.handoffContext ? (
                  <ChevronDown size={18} className="text-gray-400" />
                ) : (
                  <ChevronRight size={18} className="text-gray-400" />
                )}
              </button>
              {expandedSections.handoffContext && (
                <div className="px-4 pb-4 text-sm text-dark-text markdown-content">
                  {currentState.handoff_context ? (
                    <ReactMarkdown>{currentState.handoff_context}</ReactMarkdown>
                  ) : (
                    <p className="text-gray-500 italic">(empty)</p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
