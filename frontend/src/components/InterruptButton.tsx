import React from 'react'
import { Square } from 'lucide-react'

interface InterruptButtonProps {
    onInterrupt: () => void
    isStreaming: boolean
}

export function InterruptButton({ onInterrupt, isStreaming }: InterruptButtonProps): React.ReactElement | null {
    if (!isStreaming) return null

    return (
        <button
            onClick={onInterrupt}
            className="p-3 bg-red-600 hover:bg-red-700 text-white rounded-full shadow-lg transition-all animate-pulse z-50"
            title="Interrupt generation"
            aria-label="Interrupt"
        >
            <Square size={20} fill="currentColor" />
        </button>
    )
}
