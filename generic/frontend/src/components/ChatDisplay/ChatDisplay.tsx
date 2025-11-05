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
} from '../../hooks/useStore'

export function ChatDisplay(): React.ReactElement {
  const messages = useMessages()
  const isStreaming = useIsStreaming()
  const isInterrupted = useIsInterrupted()
  const selectedAgent = useSelectedAgent()
  const trimCount = useTrimCount()
  const toolCallsByNodeId = useToolCallsByNodeId()
  const toolExecutionsByNodeId = useToolExecutionsByNodeId()
  const conversationTree = useConversationTree()

  const { sendUserMessage, sendInterrupt } = useMessageActions()
  const { setSelectedAgent, setTrimCount } = useUserInteractionActions()

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // Build ordered list of all conversation items (messages, tool calls, executions) from tree
  const conversationItems = React.useMemo(() => {
    if (!conversationTree) return []

    const items: Array<{ type: 'message' | 'tool_call' | 'tool_execution'; data: any; nodeId: string }> = []

    console.log('[ChatDisplay] Building conversation items from tree...')
    console.log('[ChatDisplay] Tree root:', conversationTree)
    console.log('[ChatDisplay] toolCallsByNodeId:', toolCallsByNodeId)
    console.log('[ChatDisplay] toolExecutionsByNodeId:', toolExecutionsByNodeId)

    const traverse = (node: any, depth: number = 0) => {
      const indent = '  '.repeat(depth)
      console.log(`${indent}[ChatDisplay] Traversing node: id=${node.id}, type=${node.node_type}, agent=${node.agent_name}`)

      if (node.node_type === 'message') {
        const message = messages.find(m => m.node_id === node.id)
        if (message) {
          console.log(`${indent}  -> Added message item`)
          items.push({ type: 'message', data: message, nodeId: node.id })
        } else {
          console.log(`${indent}  -> Message node but no message data found!`)
        }
      } else if (node.node_type === 'tool_call') {
        console.log(`${indent}  -> Found tool_call node`)
        const toolCall = toolCallsByNodeId[node.id]
        if (toolCall) {
          console.log(`${indent}  -> Added tool_call item:`, toolCall)
          items.push({ type: 'tool_call', data: toolCall, nodeId: node.id })
        } else {
          console.log(`${indent}  -> tool_call node but no ToolCall data found!`)
        }
        const toolExecution = toolExecutionsByNodeId[node.id]
        if (toolExecution) {
          console.log(`${indent}  -> Added tool_execution item:`, toolExecution)
          items.push({ type: 'tool_execution', data: toolExecution, nodeId: node.id })
        } else {
          console.log(`${indent}  -> No tool_execution data yet`)
        }
      } else {
        console.log(`${indent}  -> Unknown node_type: ${node.node_type}`)
      }

      // Traverse children
      if (node.children && node.children.length > 0) {
        node.children.forEach((child: any) => traverse(child, depth + 1))
      }
    }

    traverse(conversationTree)
    console.log(`[ChatDisplay] Total conversation items: ${items.length}`)
    return items
  }, [conversationTree, messages, toolCallsByNodeId, toolExecutionsByNodeId])

  // Auto-scroll to latest message when new conversation items arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [conversationItems])

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
        {conversationItems.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 text-sm">No messages yet. Waiting for agent run to start...</p>
          </div>
        ) : (
          <div className="space-y-2">
            {conversationItems.map((item, index) => {
              if (item.type === 'message') {
                const message = item.data
                const messageIndex = messages.findIndex(m => m.node_id === message.node_id)
                return (
                  <MessageItem
                    key={`msg-${item.nodeId}`}
                    message={message}
                    messageIndex={messageIndex}
                    totalMessages={messages.length}
                    onSetTrimPoint={handleSetTrimPoint}
                    isInterrupted={isInterrupted}
                  />
                )
              } else if (item.type === 'tool_call') {
                return <ToolCallItem key={`tc-${item.nodeId}`} toolCall={item.data} />
              } else if (item.type === 'tool_execution') {
                return <ToolExecutionItem key={`te-${item.nodeId}`} toolExecution={item.data} />
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
