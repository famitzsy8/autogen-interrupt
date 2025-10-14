/**
 * MessageItem component displays a single agent message with interactive controls.
 *
 * Features:
 * - Displays agent name with configured color
 * - Shows message content
 * - Provides chat icon for setting trim count
 * - Calculates message index for trim count functionality
 */

import React from 'react'
import { MessageCircle } from 'lucide-react'
import { getAgentColor, getAgentDisplayName } from '../../constants/agents'
import type { AgentMessage } from '../../types'

interface MessageItemProps {
  message: AgentMessage
  messageIndex: number
  totalMessages: number
  onSetTrimPoint: (trimCount: number) => void
  isInterrupted: boolean
}

export function MessageItem({
  message,
  messageIndex,
  totalMessages,
  onSetTrimPoint,
  isInterrupted,
}: MessageItemProps): React.ReactElement {
  const agentColor = getAgentColor(message.agent_name)
  const displayName = getAgentDisplayName(message.agent_name)

  // Calculate trim count: number of messages from this point to the end
  const trimCount = totalMessages - messageIndex - 1

  const handleSetTrimPoint = (): void => {
    if (isInterrupted) {
      onSetTrimPoint(trimCount)
    }
  }

  return (
    <div className="mb-4 group">
      {/* Agent name with color indicator */}
      <div className="flex items-center gap-2 mb-1">
        <div
          className="w-3 h-3 rounded-full"
          style={{ backgroundColor: agentColor }}
          aria-label={`${displayName} indicator`}
        />
        <span className="text-sm font-medium text-dark-text">{displayName}</span>
      </div>

      {/* Message content */}
      <div
        className="pl-5 py-2 px-3 rounded border border-dark-border bg-dark-hover"
        style={{
          borderLeftColor: agentColor,
          borderLeftWidth: '3px',
        }}
      >
        <p className="text-dark-text text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </p>
      </div>

      {/* Chat icon for trim point selection - only show when interrupted */}
      {isInterrupted && (
        <div className="flex items-center mt-1 pl-5">
          <button
            onClick={handleSetTrimPoint}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-dark-accent transition-colors opacity-0 group-hover:opacity-100"
            aria-label={`Set trim point at ${displayName}'s message (trim ${trimCount} messages)`}
            title={`Branch from this message (removes ${trimCount} messages)`}
          >
            <MessageCircle size={14} />
            <span>Branch here ({trimCount})</span>
          </button>
        </div>
      )}
    </div>
  )
}
