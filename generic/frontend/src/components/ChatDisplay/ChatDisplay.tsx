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
import { ToolCallItem } from './ToolCallItem'
import { ToolExecutionItem } from './ToolExecutionItem'
import { InterruptButton } from './InterruptButton'
import { UserInput } from './UserInput'
import { X } from 'lucide-react'
import {
  useMessages,
  useIsStreaming,
  useIsInterrupted,
  useSelectedAgent,
  useTrimCount,
  useMessageActions,
  useUserInteractionActions,
  useToolCallsByNodeId,
  useToolExecutionsByNodeId,
  useConversationTree,
  useSelectedNodeIdForChat,
  useChatFocusTarget,
  useChatDisplayActions,
} from '../../hooks/useStore'
import type { ConversationItemType } from '../../types'

export function ChatDisplay(): React.ReactElement {
  const messages = useMessages()
  const isStreaming = useIsStreaming()
  const isInterrupted = useIsInterrupted()
  const selectedAgent = useSelectedAgent()
  const trimCount = useTrimCount()
  const toolCallsByNodeId = useToolCallsByNodeId()
  const toolExecutionsByNodeId = useToolExecutionsByNodeId()
  const conversationTree = useConversationTree()
  const selectedNodeIdForChat = useSelectedNodeIdForChat()
  const chatFocusTarget = useChatFocusTarget()

  const { sendUserMessage, sendInterrupt } = useMessageActions()
  const { setSelectedAgent, setTrimCount } = useUserInteractionActions()
  const { setChatFocusTarget, setChatDisplayVisible } = useChatDisplayActions()

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const conversationItemRefs = useRef<Record<string, HTMLDivElement | null>>({})

  const getConversationItemKey = (nodeId: string, type: ConversationItemType): string => `${type}:${nodeId}`

  // Build ordered list of all conversation items (messages, tool calls, executions) from tree
  const conversationItems = React.useMemo(() => {
    if (!conversationTree) return []

    const items: Array<{ type: 'message' | 'tool_call' | 'tool_execution'; data: any; nodeId: string }> = []

    const traverse = (node: any) => {
      if (node.node_type === 'message') {
        const message = messages.find(m => m.node_id === node.id)
        if (message) {
          items.push({ type: 'message', data: message, nodeId: node.id })
        }
      } else if (node.node_type === 'tool_call') {
        const toolCall = toolCallsByNodeId[node.id]
        if (toolCall) {
          items.push({ type: 'tool_call', data: toolCall, nodeId: node.id })
        }
        const toolExecution = toolExecutionsByNodeId[node.id]
        if (toolExecution) {
          items.push({ type: 'tool_execution', data: toolExecution, nodeId: node.id })
        }
      }

      // Traverse children
      if (node.children && node.children.length > 0) {
        node.children.forEach((child: any) => traverse(child))
      }
    }

    traverse(conversationTree)
    return items
  }, [conversationTree, messages, toolCallsByNodeId, toolExecutionsByNodeId])

  // Scroll to selected message when a node is clicked in the tree
  useEffect(() => {
    if (!chatFocusTarget) return

    const key = getConversationItemKey(chatFocusTarget.nodeId, chatFocusTarget.itemType)
    const targetElement = conversationItemRefs.current[key]

    if (targetElement && messagesContainerRef.current) {
      const container = messagesContainerRef.current
      // Get the element's position relative to the scrollable container
      const itemTop = targetElement.offsetTop
      // Account for container's padding (p-4 = 16px) and space-y-2 (8px between items)
      // We want the message to appear at the top, so subtract these offsets
      const containerPadding = 16
      const itemSpacing = 80

      container.scrollTo({
        top: itemTop - containerPadding - itemSpacing,
        behavior: 'smooth'
      })
    }
  }, [chatFocusTarget, conversationItems])

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

  const handleCloseChatDisplay = (): void => {
    setChatDisplayVisible(false)
  }

  // Auto-clear selection on user scroll (but not during programmatic scroll to selection)
  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container || !chatFocusTarget) return

    let isUserScroll = false
    const scrollTimeout = setTimeout(() => {
      // After initial programmatic scroll, any scroll is user-initiated
      isUserScroll = true
    }, 500) // Wait for initial scroll animation to complete

    const handleScroll = () => {
      if (isUserScroll) {
        setChatFocusTarget(null)
      }
    }

    container.addEventListener('scroll', handleScroll)
    return () => {
      clearTimeout(scrollTimeout)
      container.removeEventListener('scroll', handleScroll)
    }
  }, [chatFocusTarget, setChatFocusTarget])

  return (
    <div className="flex flex-col h-full bg-dark-bg">
      {/* Header */}
      <div className="border-b border-dark-border p-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-dark-text">Agent Conversation</h2>
          </div>
          <button
            onClick={handleCloseChatDisplay}
            className="p-2 text-gray-400 hover:text-gray-200 hover:bg-dark-hover rounded transition-colors"
            aria-label="Close chat display"
            title="Hide chat display"
          >
            <X size={20} />
          </button>
        </div>
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
        {conversationItems.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 text-sm">No messages yet. Waiting for agent run to start...</p>
          </div>
        ) : (
          <div className="space-y-2">
            {conversationItems.map((item) => {
              const itemKey = getConversationItemKey(item.nodeId, item.type)
              const isFocused =
                chatFocusTarget?.nodeId === item.nodeId && chatFocusTarget.itemType === item.type

              if (item.type === 'message') {
                const message = item.data
                const messageIndex = messages.findIndex(m => m.node_id === message.node_id)
                const fallbackSelected = !chatFocusTarget && selectedNodeIdForChat === item.nodeId
                const isSelected = isFocused || fallbackSelected
                return (
                  <div
                    key={`msg-${item.nodeId}`}
                    ref={(el) => { conversationItemRefs.current[itemKey] = el }}
                    className={`transition-all ${isSelected ? 'ring-2 ring-blue-500 ring-opacity-50 rounded' : ''}`}
                  >
                    <MessageItem
                      message={message}
                      messageIndex={messageIndex}
                      totalMessages={messages.length}
                      onSetTrimPoint={handleSetTrimPoint}
                      isInterrupted={isInterrupted}
                    />
                  </div>
                )
              } else if (item.type === 'tool_call') {
                return (
                  <div
                    key={`tc-${item.nodeId}`}
                    ref={(el) => { conversationItemRefs.current[itemKey] = el }}
                    className={`transition-all ${isFocused ? 'ring-2 ring-blue-500 ring-opacity-50 rounded' : ''}`}
                  >
                    <ToolCallItem toolCall={item.data} />
                  </div>
                )
              } else if (item.type === 'tool_execution') {
                return (
                  <div
                    key={`te-${item.nodeId}`}
                    ref={(el) => { conversationItemRefs.current[itemKey] = el }}
                    className={`transition-all ${isFocused ? 'ring-2 ring-green-500 ring-opacity-50 rounded' : ''}`}
                  >
                    <ToolExecutionItem toolExecution={item.data} />
                  </div>
                )
              }
              return null
            })}
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
