/**
 * ChatDisplay is the main container for the chat interface.
 *
 * Features:
 * - Displays all agent messages in vertical scrollable list
 * - Shows interrupt button when stream is active
 * - Provides user input area with agent selection
 * - Auto-scrolls to latest message
 * - Handles trim point selection for branching
 * - Integrates with Zustand store for state management
 */

import React, { useEffect, useRef } from 'react'
import { MessageItem } from './MessageItem'
import { InterruptButton } from './InterruptButton'
import { UserInput } from './UserInput'
import {
  useMessages,
  useIsStreaming,
  useIsInterrupted,
  useSelectedAgent,
  useTrimCount,
  useMessageActions,
  useUserInteractionActions,
} from '../../hooks/useDebateStore'

export function ChatDisplay(): React.ReactElement {
  const messages = useMessages()
  const isStreaming = useIsStreaming()
  const isInterrupted = useIsInterrupted()
  const selectedAgent = useSelectedAgent()
  const trimCount = useTrimCount()

  const { sendUserMessage, sendInterrupt } = useMessageActions()
  const { setSelectedAgent, setTrimCount } = useUserInteractionActions()

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to latest message when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  const handleInterrupt = (): void => {
    try {
      sendInterrupt()
      setTrimCount(0) // Reset trim count on interrupt
    } catch (error) {
      console.error('Failed to send interrupt:', error)
    }
  }

  const handleSendMessage = (content: string, targetAgent: string, currentTrimCount: number): void => {
    try {
      sendUserMessage(content, targetAgent, currentTrimCount)
    } catch (error) {
      console.error('Failed to send user message:', error)
    }
  }

  const handleSetTrimPoint = (newTrimCount: number): void => {
    setTrimCount(newTrimCount)
  }

  return (
    <div className="flex flex-col h-full bg-dark-bg">
      {/* Header */}
      <div className="border-b border-dark-border p-4">
        <h2 className="text-xl font-semibold text-dark-text">Agent Conversation</h2>
        <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
          <div
            className={`w-2 h-2 rounded-full ${
              isStreaming ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
            }`}
          />
          <span>
            {isStreaming
              ? 'Stream active'
              : isInterrupted
                ? 'Interrupted - waiting for input'
                : 'Idle'}
          </span>
        </div>
      </div>

      {/* Messages list */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 text-sm">No messages yet. Waiting for debate to start...</p>
          </div>
        ) : (
          <div className="space-y-2">
            {messages.map((message, index) => (
              <MessageItem
                key={message.node_id}
                message={message}
                messageIndex={index}
                totalMessages={messages.length}
                onSetTrimPoint={handleSetTrimPoint}
                isInterrupted={isInterrupted}
              />
            ))}
            {/* Scroll anchor */}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Interrupt button */}
      <InterruptButton onInterrupt={handleInterrupt} isStreaming={isStreaming} />

      {/* User input area */}
      <UserInput
        onSendMessage={handleSendMessage}
        isInterrupted={isInterrupted}
        selectedAgent={selectedAgent}
        onSelectAgent={setSelectedAgent}
        trimCount={trimCount}
      />
    </div>
  )
}
