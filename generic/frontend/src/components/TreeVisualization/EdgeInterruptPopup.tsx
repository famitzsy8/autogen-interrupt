/**
 * EdgeInterruptPopup component displays a popup for sending messages when an edge is clicked.
 *
 * Features:
 * - Positioned next to the clicked edge
 * - Agent selection dropdown
 * - Message input textarea
 * - Send and cancel buttons
 * - Only shows when interrupt is acknowledged
 */

import React, { useState, useRef, useEffect } from 'react'
import { Send, X } from 'lucide-react'
import { getAgentDisplayName } from '../../constants/agents'
import { useParticipantNames, useIsInterrupted } from '../../hooks/useStore'

interface EdgeInterruptPopupProps {
  position: { x: number; y: number }
  targetNodeId: string
  trimCount: number
  onSendMessage: (content: string, targetAgent: string, trimCount: number) => void
  onClose: () => void
}

export function EdgeInterruptPopup({
  position,
  targetNodeId,
  trimCount,
  onSendMessage,
  onClose,
}: EdgeInterruptPopupProps): React.ReactElement | null {
  const [messageContent, setMessageContent] = useState('')
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const popupRef = useRef<HTMLDivElement>(null)

  const participantNames = useParticipantNames()
  const availableAgents = participantNames?.participant_names || []
  const isInterrupted = useIsInterrupted()

  // Close popup when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent): void => {
      if (popupRef.current && !popupRef.current.contains(event.target as Node)) {
        onClose()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [onClose])

  // Don't show popup until interrupt is acknowledged
  if (!isInterrupted) {
    return null
  }

  const handleSend = (): void => {
    if (!messageContent.trim() || !selectedAgent) {
      return
    }

    // Use the calculated trim_count to branch at the clicked edge
    // This trims all messages after the target node
    onSendMessage(messageContent.trim(), selectedAgent, trimCount)
    setMessageContent('')
    onClose()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>): void => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleSend()
    }
  }

  const canSend = messageContent.trim().length > 0 && selectedAgent !== null

  return (
    <div
      ref={popupRef}
      className="absolute bg-dark-bg border-2 border-dark-accent rounded-lg shadow-xl p-4 z-50 w-80"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        transform: 'translate(-50%, 10px)',
      }}
    >
      {/* Header with close button */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-dark-text">Branch Conversation</h3>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-dark-text transition-colors"
          aria-label="Close"
        >
          <X size={18} />
        </button>
      </div>

      {/* Agent selection dropdown */}
      <div className="mb-3 relative">
        <label htmlFor="edge-agent-select" className="block text-xs text-gray-500 mb-1">
          Target Agent
        </label>
        <button
          onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          className="w-full flex items-center justify-between px-3 py-2 bg-dark-hover border border-dark-border rounded text-sm hover:border-dark-accent transition-colors"
          aria-label="Select target agent"
        >
          <span className={selectedAgent ? 'text-dark-text' : 'text-gray-500'}>
            {selectedAgent ? getAgentDisplayName(selectedAgent) : 'Select an agent...'}
          </span>
          <svg
            className="w-4 h-4 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* Dropdown menu */}
        {isDropdownOpen && (
          <div className="absolute z-10 w-full mt-1 bg-dark-hover border border-dark-border rounded shadow-lg max-h-48 overflow-y-auto">
            {availableAgents.length === 0 ? (
              <div className="px-3 py-2 text-sm text-gray-500">No agents available</div>
            ) : (
              availableAgents.map((agent) => (
                <button
                  key={agent}
                  onClick={() => {
                    setSelectedAgent(agent)
                    setIsDropdownOpen(false)
                  }}
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

      {/* Message input area */}
      <div className="mb-3">
        <label htmlFor="edge-message-input" className="block text-xs text-gray-500 mb-1">
          Message
        </label>
        <textarea
          id="edge-message-input"
          value={messageContent}
          onChange={(e) => setMessageContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message... (Ctrl+Enter to send)"
          className="w-full px-3 py-2 bg-dark-hover border border-dark-border rounded text-sm text-dark-text placeholder-gray-500 resize-none focus:outline-none focus:border-dark-accent transition-colors"
          rows={3}
          aria-label="Message input"
        />
      </div>

      {/* Send button */}
      <button
        onClick={handleSend}
        disabled={!canSend}
        className={`w-full flex items-center justify-center gap-2 px-4 py-2 rounded transition-colors ${
          canSend
            ? 'bg-dark-accent text-white hover:bg-blue-600'
            : 'bg-dark-hover text-gray-500 cursor-not-allowed'
        }`}
        aria-label="Send message"
      >
        <Send size={18} />
        <span className="text-sm font-medium">Send</span>
      </button>
    </div>
  )
}
