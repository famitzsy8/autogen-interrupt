/**
 * Terminate Button Component
 *
 * A button to gracefully terminate the agent run and display final state.
 * Unlike the interrupt button which pauses the stream, this ends the run completely.
 */

import { StopCircle } from 'lucide-react'
import { useTerminationActions, useIsStreaming } from '../hooks/useStore'

export function TerminateButton(): React.ReactElement | null {
    const isStreaming = useIsStreaming()
    const { sendTerminateRequest } = useTerminationActions()

    // Only show when streaming
    if (!isStreaming) return null

    const handleTerminate = () => {
        try {
            sendTerminateRequest()
        } catch (error) {
            console.error('Failed to send terminate request:', error)
        }
    }

    return (
        <button
            onClick={handleTerminate}
            className="px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg shadow-lg transition-all z-50 flex items-center gap-2 min-w-[120px] justify-center"
            title="Terminate run and view final state"
            aria-label="Terminate Run"
        >
            <StopCircle size={20} />
            <span className="font-medium">Terminate</span>
        </button>
    )
}
