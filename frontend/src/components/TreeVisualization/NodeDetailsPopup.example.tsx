/**
 * Example usage of NodeDetailsPopup component.
 *
 * This file demonstrates how to use the NodeDetailsPopup component
 * with different data scenarios.
 */

import React, { useState } from 'react'
import { NodeDetailsPopup } from './NodeDetailsPopup'
import type { TreeNode, StateUpdate, ToolCall, ToolExecution } from '../../types'
import { MessageType } from '../../types'

export function NodeDetailsPopupExample(): React.ReactElement {
  const [isOpen, setIsOpen] = useState(false)

  // Example node data
  const exampleNode: TreeNode = {
    id: 'node-123',
    agent_name: 'research_agent',
    display_name: 'Research Agent',
    message: '# Research Results\n\nI found the following information:\n\n- Point 1: Important fact\n- Point 2: Another key finding\n\n```python\nprint("Hello, World!")\n```',
    summary: 'Completed research on topic X and found key insights',
    parent: null,
    children: [],
    is_active: true,
    branch_id: 'branch-1',
    timestamp: new Date().toISOString(),
    node_type: 'message',
  }

  // Example state update
  const exampleStateUpdate: StateUpdate = {
    type: MessageType.STATE_UPDATE,
    timestamp: new Date().toISOString(),
    state_of_run: '## Current Progress\n\n- Completed initial research\n- Found 3 relevant sources\n\n**Next Steps:**\n1. Analyze findings\n2. Prepare summary',
    tool_call_facts: '### Facts Gathered\n\n- Fact 1: Data point A\n- Fact 2: Data point B\n- Fact 3: Data point C',
    handoff_context: '## Agent Selection Rules\n\n- Use Research Agent for information gathering\n- Use Analysis Agent for data processing\n- Use Writing Agent for final output',
    message_index: 5,
  }

  // Example tool call
  const exampleToolCall: ToolCall = {
    type: MessageType.TOOL_CALL,
    timestamp: new Date().toISOString(),
    agent_name: 'research_agent',
    node_id: 'node-123',
    tools: [
      {
        id: 'call-1',
        name: 'web_search',
        arguments: '{"query": "latest AI research", "max_results": 5}',
      },
      {
        id: 'call-2',
        name: 'fetch_document',
        arguments: '{"url": "https://example.com/paper.pdf"}',
      },
    ],
  }

  // Example tool execution
  const exampleToolExecution: ToolExecution = {
    type: MessageType.TOOL_EXECUTION,
    timestamp: new Date().toISOString(),
    agent_name: 'research_agent',
    node_id: 'node-123',
    results: [
      {
        tool_call_id: 'call-1',
        tool_name: 'web_search',
        success: true,
        result: 'Found 5 results:\n1. Paper A\n2. Paper B\n3. Paper C\n4. Paper D\n5. Paper E',
      },
      {
        tool_call_id: 'call-2',
        tool_name: 'fetch_document',
        success: false,
        result: 'Error: Document not found (404)',
      },
    ],
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-dark-text mb-4">NodeDetailsPopup Example</h1>

      <button
        onClick={() => setIsOpen(true)}
        className="px-4 py-2 bg-dark-accent text-white rounded hover:bg-blue-600 transition-colors"
      >
        Open Node Details Popup
      </button>

      {isOpen && (
        <NodeDetailsPopup
          node={exampleNode}
          stateUpdate={exampleStateUpdate}
          toolCall={exampleToolCall}
          toolExecution={exampleToolExecution}
          onClose={() => setIsOpen(false)}
        />
      )}
    </div>
  )
}
