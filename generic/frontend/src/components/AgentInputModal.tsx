/**
 * Agent Input Modal Component
 *
 * Displays a compact modal in the tree area when an agent requests human input.
 * Does not block the chat display but prevents tree interaction.
 */

import React, { useEffect, useRef } from 'react'
import { useAgentInputActions, useAgentInputDraft } from '../hooks/useStore'
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
      className="absolute inset-0 z-40 flex items-end justify-center pb-20 px-4 pointer-events-none"
      style={{ pointerEvents: 'none' }}
    >
      {/* Backdrop for tree area only - blocks mouse interaction */}
      <div
        className="absolute inset-0 bg-black bg-opacity-30"
        style={{ pointerEvents: 'auto' }}
        onClick={(e) => {
          if (e.target === e.currentTarget && onCancel) {
            onCancel()
          }
        }}
      />

      {/* Compact modal card */}
      <div
        className="relative bg-gray-800 border border-gray-600 rounded-lg shadow-2xl max-w-xl w-full"
        style={{ pointerEvents: 'auto' }}
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
