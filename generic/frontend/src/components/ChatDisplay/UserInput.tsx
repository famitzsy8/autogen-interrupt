/**
 * UserInput component handles user message composition and agent targeting.
 *
 * Features:
 * - Text area for message input
 * - Agent selection dropdown (dynamically populated from team config)
 * - Active/inactive send button based on interrupt state
 * - Displays current trim count
 * - Clears input after successful send
 */

import React, { useState } from 'react'
import { Send, ChevronDown } from 'lucide-react'
import { getAgentDisplayName } from '../../constants/agents'
import { useParticipantNames } from '../../hooks/useStore'

interface UserInputProps {
  onSendMessage: (content: string, targetAgent: string, trimCount: number) => void
  isInterrupted: boolean
  selectedAgent: string | null
  onSelectAgent: (agent: string) => void
  trimCount: number
}

export function UserInput({
  onSendMessage,
  isInterrupted,
  selectedAgent,
  onSelectAgent,
  trimCount,
}: UserInputProps): React.ReactElement {
  const [messageContent, setMessageContent] = useState('')
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)

  // Get participant names (individual agents) from backend
  const participantNames = useParticipantNames()
  const availableAgents = participantNames?.participant_names || []

  const handleSend = (): void => {
    if (!isInterrupted || !messageContent.trim() || !selectedAgent) {
      return
    }

    onSendMessage(messageContent.trim(), selectedAgent, trimCount)
    setMessageContent('')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>): void => {
    // Send on Ctrl+Enter or Cmd+Enter
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSelectAgent = (agent: string): void => {
    onSelectAgent(agent)
    setIsDropdownOpen(false)
  }

  const canSend = isInterrupted && messageContent.trim().length > 0 && selectedAgent !== null

  return (
    <div className="border-t border-dark-border p-4 bg-dark-bg">
      {/* Agent selection dropdown */}
      <div className="mb-3 relative">
        <label htmlFor="agent-select" className="block text-xs text-gray-500 mb-1">
          Target Agent
        </label>
        <button
          onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          className="w-full flex items-center justify-between px-3 py-2 bg-dark-hover border border-dark-border rounded text-sm hover:border-dark-accent transition-colors"
          aria-label="Select target agent"
          disabled={!isInterrupted}
        >
          <span className={selectedAgent ? 'text-dark-text' : 'text-gray-500'}>
            {selectedAgent ? getAgentDisplayName(selectedAgent) : 'Select an agent...'}
          </span>
          <ChevronDown size={16} className="text-gray-500" />
        </button>

        {/* Dropdown menu */}
        {isDropdownOpen && isInterrupted && (
          <div className="absolute z-10 w-full mt-1 bg-dark-hover border border-dark-border rounded shadow-lg max-h-48 overflow-y-auto">
            {availableAgents.length === 0 ? (
              <div className="px-3 py-2 text-sm text-gray-500">
                No agents available
              </div>
            ) : (
              availableAgents.map((agent) => (
                <button
                  key={agent}
                  onClick={() => handleSelectAgent(agent)}
                  className={`w-full text-left px-3 py-2 text-sm hover:bg-dark-border transition-colors ${
                    selectedAgent === agent ? 'bg-dark-border text-dark-accent' : 'text-dark-text'
                  }`}
                >
                  {getAgentDisplayName(agent)}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Trim count display */}
      {isInterrupted && trimCount > 0 && (
        <div className="mb-2 text-xs text-gray-500">
          Branching from {trimCount} message{trimCount !== 1 ? 's' : ''} back
        </div>
      )}

      {/* Message input area */}
      <div className="flex gap-2">
        <textarea
          value={messageContent}
          onChange={(e) => setMessageContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isInterrupted
              ? 'Type your message... (Ctrl+Enter to send)'
              : 'Interrupt the stream to send a message'
          }
          className="flex-1 px-3 py-2 bg-dark-hover border border-dark-border rounded text-sm text-dark-text placeholder-gray-500 resize-none focus:outline-none focus:border-dark-accent transition-colors"
          rows={3}
          disabled={!isInterrupted}
          aria-label="User message input"
        />
        <button
          onClick={handleSend}
          disabled={!canSend}
          className={`px-4 flex items-center gap-2 rounded transition-colors ${
            canSend
              ? 'bg-dark-accent text-white hover:bg-blue-600'
              : 'bg-dark-hover text-gray-500 cursor-not-allowed'
          }`}
          aria-label="Send message"
          title={!isInterrupted ? 'Interrupt the stream first' : 'Send message to selected agent'}
        >
          <Send size={18} />
        </button>
      </div>

      {/* Help text */}
      <div className="mt-2 text-xs text-gray-600">
        {isInterrupted
          ? 'Select an agent and type your message to continue the conversation'
          : 'Click "Interrupt" to pause the conversation and send a message'}
      </div>
    </div>
  )
}
