/**
 * Agent Input Modal Component
 *
 * Displays a compact modal in the tree area when an agent requests human input.
 * When triggered by analysis, displays highlighted analysis components with their
 * descriptions and expandable reasoning.
 * Does not block the chat display but prevents tree interaction.
 */

import React, { useEffect, useRef, useState } from 'react'
import { AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'
import { useAgentInputActions, useAgentInputDraft } from '../hooks/useStore'
import { useStore } from '../store/store'
import { AgentBadge } from './AgentBadge'
import type { AgentInputRequest } from '../types'

interface AgentInputModalProps {
  request: AgentInputRequest
  onSubmit: (userInput: string) => void
  onCancel?: () => void
}

interface ExpandedComponent {
  [label: string]: boolean
}

export const AgentInputModal: React.FC<AgentInputModalProps> = ({
  request,
  onSubmit,
  onCancel,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const agentInputDraft = useAgentInputDraft()
  const { setHumanInputDraft } = useAgentInputActions()
  const [expandedComponents, setExpandedComponents] = useState<ExpandedComponent>({})

  // Get analysis components from store
  const analysisComponents = useStore((state) => state.analysisComponents)

  // Check if feedback_context exists (analysis triggered)
  const { feedback_context } = request
  const hasFeedbackContext = !!feedback_context

  // Toggle component expansion
  const toggleComponentExpanded = (label: string) => {
    setExpandedComponents((prev) => ({
      ...prev,
      [label]: !prev[label],
    }))
  }

  // Focus textarea when modal opens
  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (agentInputDraft.trim()) {
      onSubmit(agentInputDraft)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Submit on Ctrl+Enter or Cmd+Enter
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      handleSubmit(e)
    }
    // Cancel on Escape
    if (e.key === 'Escape' && onCancel) {
      onCancel()
    }
  }

  return (
    <div
      className="absolute bottom-20 left-1/2 transform -translate-x-1/2 z-40 flex items-end justify-center px-4 pointer-events-none"
    >
      {/* Compact modal card - pointer events auto to allow interaction within the card */}
      <div
        className="relative bg-gray-800 border border-gray-600 rounded-lg shadow-2xl max-w-3xl w-full pointer-events-auto max-h-[80vh] overflow-y-auto"
        role="dialog"
        aria-labelledby="agent-input-modal-title"
      >
        {/* Header bar */}
        <div className="bg-gray-700 px-4 py-2 rounded-t-lg border-b border-gray-600">
          <h3
            id="agent-input-modal-title"
            className="text-sm font-semibold text-gray-200 flex items-center gap-2"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <AgentBadge agentName={request.agent_name} size="sm" />
            <span>needs input</span>
          </h3>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-4">
          {/* Prompt message */}
          <p className="text-sm text-gray-300 mb-3 whitespace-pre-wrap">
            {request.prompt}
          </p>

          {/* Feedback Context Section - Only shown when analysis triggered */}
          {hasFeedbackContext && feedback_context && (
            <div className="mb-6 space-y-4">
              {/* Alert Banner */}
              <div className="flex gap-3 p-3 bg-amber-950/40 rounded-lg border border-amber-700/50">
                <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <strong className="text-amber-300 text-sm font-semibold block mb-1">
                    Analysis Alert
                  </strong>
                  <p className="text-xs text-gray-300">
                    The following components triggered above the threshold. Review the details and provide feedback.
                  </p>
                </div>
              </div>


              {/* Triggered Components with Details */}
              {feedback_context.triggered_with_details && Object.entries(feedback_context.triggered_with_details).length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(feedback_context.triggered_with_details).map(([label, details]) => {
                    const component = analysisComponents.find((c) => c.label === label)
                    const isExpanded = expandedComponents[label] || false

                    return (
                      <div
                        key={label}
                        className="rounded-lg border border-gray-600/50 bg-gray-800/30 overflow-hidden hover:border-gray-500/70 transition-colors"
                      >
                        {/* Component Header - Clickable to expand/collapse */}
                        <button
                          onClick={() => toggleComponentExpanded(label)}
                          className="w-full px-4 py-3 flex items-start gap-3 hover:bg-gray-800/50 transition-colors text-left"
                        >
                          {/* Color Indicator Circle */}
                          <div
                            className="w-3 h-3 rounded-full flex-shrink-0 mt-1"
                            style={{ backgroundColor: component?.color || '#6b7280' }}
                          />

                          {/* Component Info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-baseline gap-2 mb-1">
                              <h4 className="text-sm font-semibold text-gray-100 break-words">
                                {label}
                              </h4>
                              <span className="text-xs font-bold text-red-400 flex-shrink-0">
                                {details.score}/10
                              </span>
                            </div>
                            <p className="text-xs text-gray-400 line-clamp-2">
                              {details.description}
                            </p>
                          </div>

                          {/* Expand/Collapse Icon */}
                          <div className="flex-shrink-0 text-gray-400">
                            {isExpanded ? (
                              <ChevronUp className="w-4 h-4" />
                            ) : (
                              <ChevronDown className="w-4 h-4" />
                            )}
                          </div>
                        </button>

                        {/* Expanded Content */}
                        {isExpanded && (
                          <div className="px-4 py-3 bg-gray-900/40 border-t border-gray-600/30 space-y-2">
                            <div>
                              <strong className="text-xs font-semibold text-gray-300 block mb-1">
                                Why This Triggered:
                              </strong>
                              <p className="text-xs text-gray-400 leading-relaxed">
                                {details.reasoning || 'No additional reasoning provided.'}
                              </p>
                            </div>
                            <div>
                              <strong className="text-xs font-semibold text-gray-300 block mb-1">
                                Full Description:
                              </strong>
                              <p className="text-xs text-gray-400 leading-relaxed">
                                {details.description}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              ) : (
                /* Fallback to original display if no triggered_with_details */
                <div className="space-y-2">
                  {feedback_context.triggered.map((label) => {
                    const component = analysisComponents.find((c) => c.label === label)
                    const score = feedback_context.scores[label]

                    if (!score) return null

                    return (
                      <div
                        key={label}
                        className="p-3 bg-gray-900/50 rounded border-l-3 border-red-500"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className="px-2 py-0.5 rounded-full text-xs font-medium text-white"
                            style={{
                              backgroundColor: component?.color || '#6b7280',
                            }}
                          >
                            {label}
                          </span>
                          <span className="text-sm font-semibold text-red-400">
                            Score: {score.score}/10
                          </span>
                        </div>
                        {score.reasoning && (
                          <div className="mt-2 text-xs text-gray-400">
                            {score.reasoning}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Expandable Details Section */}
              <details className="p-3 bg-gray-900/50 rounded border border-gray-600/30">
                <summary className="cursor-pointer font-medium text-sm text-gray-300 hover:text-gray-100 transition-colors">
                  View Agent Message & Research Context
                </summary>

                <div className="mt-3 space-y-3">
                  {/* Agent Message */}
                  <div>
                    <strong className="block mb-1 text-xs font-semibold text-gray-400">
                      Agent Message:
                    </strong>
                    <pre className="p-2 bg-gray-800 rounded text-xs overflow-x-auto whitespace-pre-wrap text-gray-300">
                      {feedback_context.message
                        ? JSON.stringify(feedback_context.message, null, 2)
                        : 'N/A'}
                    </pre>
                  </div>

                  {/* Verified Facts */}
                  <div>
                    <strong className="block mb-1 text-xs font-semibold text-gray-400">
                      Verified Facts:
                    </strong>
                    <pre className="p-2 bg-gray-800 rounded text-xs overflow-x-auto whitespace-pre-wrap text-gray-300">
                      {feedback_context.tool_call_facts || '(None yet)'}
                    </pre>
                  </div>

                  {/* Research State */}
                  <div>
                    <strong className="block mb-1 text-xs font-semibold text-gray-400">
                      Research State:
                    </strong>
                    <pre className="p-2 bg-gray-800 rounded text-xs overflow-x-auto whitespace-pre-wrap text-gray-300">
                      {feedback_context.state_of_run || '(None yet)'}
                    </pre>
                  </div>
                </div>
              </details>
            </div>
          )}

          {/* Input area */}
          <textarea
            ref={textareaRef}
            value={agentInputDraft}
            onChange={(e) => setHumanInputDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full px-3 py-2 bg-gray-900 text-gray-200 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
            rows={3}
            placeholder="Type your response..."
            required
          />

          {/* Help text */}
          <p className="text-xs text-gray-500 mt-1 mb-3">
            <kbd className="px-1 py-0.5 bg-gray-700 border border-gray-600 rounded text-xs">
              Ctrl+Enter
            </kbd>{' '}
            to submit
          </p>

          {/* Buttons */}
          <div className="flex justify-end gap-2">
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="px-3 py-1.5 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
              >
                Continue
              </button>
            )}
            <button
              type="submit"
              disabled={!agentInputDraft.trim()}
              className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
            >
              Submit
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default AgentInputModal
