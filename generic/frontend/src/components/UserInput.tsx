import React, { useState, useRef, useEffect } from 'react'
import { Send, MessageSquare } from 'lucide-react'
import { useAgentDetails } from '../hooks/useStore'
import { AgentSelector } from './AgentSelector'

interface UserInputProps {
    onSendMessage: (content: string, targetAgent: string, trimCount: number) => void
    isInterrupted: boolean
    selectedAgent: string | null
    onSelectAgent: (agent: string | null) => void
    trimCount: number
}

export function UserInput({
    onSendMessage,
    isInterrupted,
    selectedAgent,
    onSelectAgent,
    trimCount,
}: UserInputProps): React.ReactElement | null {
    const [message, setMessage] = useState('')
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    const agentDetails = useAgentDetails()
    const agents = agentDetails?.agents || []

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
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
        <div className="flex flex-col gap-3 bg-dark-surface p-4 rounded-lg border border-dark-border">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-gray-400">
                    <MessageSquare size={16} />
                    <span>Send message to:</span>
                </div>
                <div className="w-64">
                    <AgentSelector
                        agents={agents}
                        selectedAgent={selectedAgent}
                        onSelectAgent={onSelectAgent}
                        disabled={!isInterrupted}
                    />
                </div>
            </div>

            <div className="relative">
                <textarea
                    ref={textareaRef}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type your message here... (Press Enter to send)"
                    className="w-full bg-dark-bg border border-dark-border rounded-md p-3 text-dark-text placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-dark-accent resize-none min-h-[80px] max-h-[200px]"
                    disabled={!isInterrupted}
                />
                <button
                    onClick={handleSend}
                    disabled={!message.trim() || !selectedAgent}
                    className="absolute bottom-3 right-3 p-2 bg-dark-accent text-white rounded-md hover:bg-opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    title="Send message"
                >
                    <Send size={16} />
                </button>
            </div>

            {trimCount > 0 && (
                <div className="text-xs text-yellow-500">
                    Note: Sending this message will trim {trimCount} future messages from the history.
                </div>
            )}
        </div>
    )
}
