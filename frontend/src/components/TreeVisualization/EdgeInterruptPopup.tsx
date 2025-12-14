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

import React, { useState, useRef } from 'react'
import { MessageCircle } from 'lucide-react'
import { FloatingInputPanel } from '../FloatingInputPanel'
import { useIsInterrupted, useEdgeInterruptMinimized } from '../../hooks/useStore'

interface EdgeInterruptPopupProps {
  position: { x: number; y: number }
  targetNodeId: string
  trimCount: number
  onSendMessage: (content: string, targetAgent: string, trimCount: number) => void
  onClose: () => void
  onMinimize: () => void
  onMaximize: () => void
}

export function EdgeInterruptPopup({
  position,
  targetNodeId: _targetNodeId,
  trimCount,
  onSendMessage,
  onClose,
  onMinimize,
  onMaximize,
}: EdgeInterruptPopupProps): React.ReactElement | null {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const popupRef = useRef<HTMLDivElement>(null)
  const isInterrupted = useIsInterrupted()
  const isMinimized = useEdgeInterruptMinimized()

  // No click-outside listener to allow interaction with the tree
  // The popup will be closed explicitly via the close button or sending a message

  // Don't show popup until interrupt is acknowledged
  if (!isInterrupted) {
    return null
  }

  // Show minimized marker instead of full popup
  if (isMinimized) {
    return (
      <div
        className="absolute z-50"
        style={{
          left: `${position.x}px`,
          top: `${position.y}px`,
          transform: 'translate(-50%, 10px)',
        }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <button
          onClick={onMaximize}
          className="group flex items-center justify-center w-10 h-10 bg-dark-accent/90 hover:bg-dark-accent rounded-full shadow-xl border-2 border-dark-border hover:border-dark-accent transition-all duration-200 hover:scale-110"
          title="Click to reopen message form"
        >
          <MessageCircle size={20} className="text-white" />
        </button>
      </div>
    )
  }

  return (
    <div
      ref={popupRef}
      className="absolute z-50"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        transform: 'translate(-50%, 10px)',
      }}
      onMouseDown={(e) => e.stopPropagation()}
    >
      <FloatingInputPanel
        onSendMessage={(content, targetAgent, trimCount) => {
          onSendMessage(content, targetAgent, trimCount)
          onClose()
        }}
        isInterrupted={isInterrupted}
        selectedAgent={selectedAgent}
        onSelectAgent={setSelectedAgent}
        trimCount={trimCount}
        onMinimize={onMinimize}
        className="shadow-xl border-dark-accent"
      />
    </div>
  )
}
