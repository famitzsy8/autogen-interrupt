/**
 * Agent Input Modal Component
 *
 * Displays a modal dialog when an agent (e.g., UserProxyAgent/fact-checker) requests
 * human input. This is role-agnostic and works for any agent type that needs human interaction.
 */

import React, { useEffect, useRef } from 'react'
import { useAgentInputActions, useAgentInputDraft } from '../hooks/useDebateStore'
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
  const { setAgentInputDraft } = useAgentInputActions()

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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      onClick={(e) => {
        // Close on backdrop click
        if (e.target === e.currentTarget && onCancel) {
          onCancel()
        }
      }}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 overflow-hidden"
        role="dialog"
        aria-labelledby="agent-input-modal-title"
        aria-describedby="agent-input-modal-description"
      >
        {/* Header */}
        <div className="bg-blue-600 dark:bg-blue-700 px-6 py-4">
          <h2
            id="agent-input-modal-title"
            className="text-xl font-semibold text-white flex items-center"
          >
            <svg
              className="w-6 h-6 mr-2"
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
            {request.agent_name} Needs Your Input
          </h2>
          <p className="text-blue-100 text-sm mt-1">
            The debate is paused waiting for your response
          </p>
        </div>

        {/* Body */}
        <div className="px-6 py-4">
          <p
            id="agent-input-modal-description"
            className="text-gray-700 dark:text-gray-300 mb-4 whitespace-pre-wrap"
          >
            {request.prompt}
          </p>

          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label
                htmlFor="agent-input-textarea"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                Your Response
              </label>
              <textarea
                ref={textareaRef}
                id="agent-input-textarea"
                value={agentInputDraft}
                onChange={(e) => setAgentInputDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white resize-vertical"
                rows={4}
                placeholder="Type your response here..."
                required
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Press <kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs">Ctrl+Enter</kbd> or <kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs">⌘+Enter</kbd> to submit
              </p>
            </div>

            {/* Footer */}
            <div className="flex justify-end space-x-3 pt-2">
              {onCancel && (
                <button
                  type="button"
                  onClick={onCancel}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                >
                  Cancel
                </button>
              )}
              <button
                type="submit"
                disabled={!agentInputDraft.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                Submit Response
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default AgentInputModal
