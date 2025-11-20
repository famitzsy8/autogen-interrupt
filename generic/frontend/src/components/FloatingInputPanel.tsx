import React, { useState, useRef, useEffect } from 'react'
import { Send, MessageSquare, X } from 'lucide-react'
import { useAgentDetails } from '../hooks/useStore'
import { AgentSelector } from './AgentSelector'

interface FloatingInputPanelProps {
    onSendMessage: (content: string, targetAgent: string, trimCount: number) => void
    isInterrupted: boolean
    selectedAgent: string | null
    onSelectAgent: (agent: string | null) => void
    trimCount: number
    onClose?: () => void // Optional close handler if needed
    className?: string
}

export function FloatingInputPanel({
    onSendMessage,
    isInterrupted,
    selectedAgent,
    onSelectAgent,
    trimCount,
    onClose,
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
                <div className="flex items-center gap-2 text-sm font-semibold text-dark-accent">
                    <MessageSquare size={16} />
                    <span>Send Message</span>
                </div>
                {onClose && (
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-300 transition-colors"
                    >
                        <X size={16} />
                    </button>
                )}
            </div>

            {/* Agent Selector */}
            <div>
                <label className="text-xs text-gray-500 mb-1 block">To Agent:</label>
                <AgentSelector
                    agents={agents}
                    selectedAgent={selectedAgent}
                    onSelectAgent={onSelectAgent}
                    disabled={!isInterrupted}
                />
            </div>

            {/* Message Input */}
            <div className="relative">
                <textarea
                    ref={textareaRef}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type your message..."
                    className="w-full bg-dark-surface border border-dark-border rounded-md p-3 pr-10 text-sm text-dark-text placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-dark-accent resize-none min-h-[80px]"
                    disabled={!isInterrupted}
                />
                <button
                    onClick={handleSend}
                    disabled={!message.trim() || !selectedAgent}
                    className="absolute bottom-2 right-2 p-1.5 bg-dark-accent text-white rounded hover:bg-opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    title="Send"
                >
                    <Send size={14} />
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
