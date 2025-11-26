import React, { useState, useRef, useEffect } from 'react'
import { ChevronRight } from 'lucide-react'
import { useAgentDetails } from '../hooks/useStore'
import { AgentSelector } from './AgentSelector'

interface FloatingInputPanelProps {
    onSendMessage: (content: string, targetAgent: string, trimCount: number) => void
    isInterrupted: boolean
    selectedAgent: string | null
    onSelectAgent: (agent: string | null) => void
    trimCount: number
    onClose?: () => void // Optional close handler if needed
    onMinimize?: () => void // Optional minimize handler (replace close behavior)
    className?: string
}

export function FloatingInputPanel({
    onSendMessage,
    isInterrupted,
    selectedAgent,
    onSelectAgent,
    trimCount,
    onClose,
    onMinimize,
    className = ''
}: FloatingInputPanelProps): React.ReactElement | null {
    const [message, setMessage] = useState('')
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    const agentDetails = useAgentDetails()
    const agents = agentDetails?.agents || []

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
        }
    }, [message])

    // Focus when interrupted
    useEffect(() => {
        if (isInterrupted && textareaRef.current) {
            textareaRef.current.focus()
        }
    }, [isInterrupted])

    const handleSend = () => {
        if (!message.trim() || !selectedAgent) return
        onSendMessage(message, selectedAgent, trimCount)
        setMessage('')
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    if (!isInterrupted) return null

    return (
        <div className={`bg-dark-bg border-2 border-dark-accent rounded-lg shadow-2xl p-4 w-96 pointer-events-auto flex flex-col gap-3 ${className}`}>
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-dark-accent">
                    Send a Message to an agent of your choice!
                </h2>
                {(onClose || onMinimize) && (
                    <button
                        onClick={onMinimize || onClose}
                        className="text-gray-500 hover:text-dark-accent transition-colors p-1 rounded hover:bg-dark-surface flex-shrink-0"
                        title="Hide panel"
                    >
                        <ChevronRight size={18} />
                    </button>
                )}
            </div>

            {/* Agent Selector */}
            <AgentSelector
                agents={agents}
                selectedAgent={selectedAgent}
                onSelectAgent={onSelectAgent}
                disabled={!isInterrupted}
            />

            {/* Message Input */}
            <div className="flex flex-col gap-3">
                <textarea
                    ref={textareaRef}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type your message..."
                    className="w-full bg-dark-surface border border-dark-border rounded-md p-3 text-sm text-dark-text placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-dark-accent resize-none min-h-[80px]"
                    disabled={!isInterrupted}
                />
                <button
                    onClick={handleSend}
                    disabled={!message.trim() || !selectedAgent}
                    className="w-full py-2.5 px-4 bg-dark-accent text-white font-semibold rounded-md hover:bg-opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                    Send
                </button>
            </div>

            {/* Trim Warning */}
            {trimCount > 0 && (
                <div className="text-xs text-yellow-500 bg-yellow-900/20 p-2 rounded border border-yellow-900/50">
                    Warning: This will trim {trimCount} future messages.
                </div>
            )}
        </div>
    )
}
