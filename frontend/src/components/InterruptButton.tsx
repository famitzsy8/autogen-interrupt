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
            className="px-4 py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-lg shadow-lg transition-all z-50 flex items-center gap-2 min-w-[120px] justify-center"
            title="Interrupt generation"
            aria-label="Interrupt"
        >
            <Square size={20} fill="currentColor" />
            <span className="font-medium">Interrupt</span>
        </button>
    )
}
