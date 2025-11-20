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
import { FloatingInputPanel } from '../FloatingInputPanel'
import { useIsInterrupted } from '../../hooks/useStore'

interface EdgeInterruptPopupProps {
  position: { x: number; y: number }
  targetNodeId: string
  trimCount: number
  onSendMessage: (content: string, targetAgent: string, trimCount: number) => void
  onClose: () => void
}

export function EdgeInterruptPopup({
  position,
  targetNodeId: _targetNodeId,
  trimCount,
  onSendMessage,
  onClose,
}: EdgeInterruptPopupProps): React.ReactElement | null {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const popupRef = useRef<HTMLDivElement>(null)
  const isInterrupted = useIsInterrupted()

  // No click-outside listener to allow interaction with the tree
  // The popup will be closed explicitly via the close button or sending a message

  // Don't show popup until interrupt is acknowledged
  if (!isInterrupted) {
    return null
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
        onClose={onClose}
        className="shadow-xl border-dark-accent"
      />
    </div>
  )
}
