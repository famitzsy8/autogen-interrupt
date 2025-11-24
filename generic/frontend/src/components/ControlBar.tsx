import React from 'react'
import { UserInput } from './UserInput'
import {
    useIsStreaming,
    useIsInterrupted,
    useSelectedAgent,
    useTrimCount,
    useMessageActions,
    useUserInteractionActions,
} from '../hooks/useStore'

export function ControlBar(): React.ReactElement | null {
    const isStreaming = useIsStreaming()
    const isInterrupted = useIsInterrupted()
    const selectedAgent = useSelectedAgent()
    const trimCount = useTrimCount()

    const { sendUserMessage } = useMessageActions()
    const { setSelectedAgent } = useUserInteractionActions()

    // Only show if we have something to show (streaming or interrupted)
    if (!isStreaming && !isInterrupted) {
        return null
    }

    const handleSendMessage = (content: string, targetAgent: string, currentTrimCount: number): void => {
        try {
            sendUserMessage(content, targetAgent, currentTrimCount)
        } catch (error) {
            // Handle error silently
        }
    }

    return (
        <div className="fixed bottom-0 left-0 right-0 bg-dark-bg border-t border-dark-border p-4 shadow-lg z-50">
            <div className="max-w-4xl mx-auto flex flex-col gap-4">
                {isInterrupted && (
                    <UserInput
                        onSendMessage={handleSendMessage}
                        isInterrupted={isInterrupted}
                        selectedAgent={selectedAgent}
                        onSelectAgent={setSelectedAgent}
                        trimCount={trimCount}
                    />
                )}
            </div>
        </div>
    )
}
