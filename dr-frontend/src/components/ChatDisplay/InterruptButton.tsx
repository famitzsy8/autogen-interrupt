/**
 * InterruptButton component allows users to interrupt the agent stream.
 *
 * Features:
 * - Only visible when stream is actively streaming
 * - Sends interrupt signal to backend
 * - Clean, minimal styling with hover states
 */

import React from 'react'
import { PauseCircle } from 'lucide-react'

interface InterruptButtonProps {
  onInterrupt: () => void
  isStreaming: boolean
}

export function InterruptButton({
  onInterrupt,
  isStreaming,
}: InterruptButtonProps): React.ReactElement | null {
  if (!isStreaming) {
    return null
  }

  return (
    <div className="border-t border-dark-border pt-3 pb-3">
      <button
        onClick={onInterrupt}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-dark-hover border border-dark-border rounded hover:bg-dark-border hover:border-dark-accent transition-colors"
        aria-label="Interrupt agent conversation"
      >
        <PauseCircle size={18} />
        <span className="text-sm font-medium">Interrupt</span>
      </button>
    </div>
  )
}
