/**
 * Agent Input Modal Component
 *
 * Displays a compact modal in the tree area when an agent requests human input.
 * Does not block the chat display but prevents tree interaction.
 */

import React, { useEffect, useRef } from 'react'
import { AlertTriangle } from 'lucide-react'
import { useAgentInputActions, useAgentInputDraft } from '../hooks/useStore'
import { useStore } from '../store/store'
import { AnalysisScoreDisplay } from './TreeVisualization/AnalysisScoreDisplay'
import type { AgentInputRequest } from '../types'

interface AgentInputModalProps {
  request: AgentInputRequest
  onSubmit: (userInput: string) => void
  onCancel?: () => void
}

export const AgentInputModal: React.FC<AgentInputModalProps> = ({
  request,
  onSubmit,
  onCancel,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const agentInputDraft = useAgentInputDraft()
  const { setHumanInputDraft } = useAgentInputActions()

  // Get analysis components from store
  const analysisComponents = useStore((state) => state.analysisComponents)

  // Check if feedback_context exists (analysis triggered)
  const { feedback_context } = request
  const hasFeedbackContext = !!feedback_context

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
            {request.agent_name} needs input
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
            <div className="mb-6 p-4 border-2 border-amber-500 rounded-lg bg-amber-950/20">
              {/* Alert Banner */}
              <div className="flex gap-3 mb-4 p-3 bg-gray-900/50 rounded-md border-l-4 border-amber-500">
                <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <strong className="text-amber-400 text-sm font-semibold block mb-1">
                    Analysis Alert
                  </strong>
                  <p className="text-xs text-gray-300">
                    The following components flagged potential issues. Please
                    review and provide feedback.
                  </p>
                </div>
              </div>

              {/* Triggered Components List */}
              <div className="space-y-2 mb-4">
                {feedback_context.triggered.map((label) => {
                  const component = analysisComponents.find(
                    (c) => c.label === label
                  )
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

              {/* Full Analysis Scores */}
              <div className="mb-4 p-3 bg-gray-900/50 rounded">
                <AnalysisScoreDisplay
                  components={analysisComponents}
                  scores={feedback_context.scores}
                  triggerThreshold={8}
                />
              </div>

              {/* Expandable Details Section */}
              <details className="p-3 bg-gray-900/50 rounded">
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
