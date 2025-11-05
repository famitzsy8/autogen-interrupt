/**
 * ToolCallItem displays a tool/function call in a collapsible format.
 * Shows which tools were called by an agent with their arguments.
 */

import React, { useState } from 'react'
import { ChevronDown, ChevronRight, Wrench } from 'lucide-react'
import type { ToolCall } from '../../types'

interface ToolCallItemProps {
  toolCall: ToolCall
}

export function ToolCallItem({ toolCall }: ToolCallItemProps): React.ReactElement {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="mb-2 pl-5">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300 transition-colors"
      >
        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <Wrench size={14} />
        <span className="font-medium">
          {toolCall.tools.length} tool{toolCall.tools.length !== 1 ? 's' : ''} called by {toolCall.agent_name}
        </span>
      </button>

      {isExpanded && (
        <div className="mt-2 ml-6 space-y-2">
          {toolCall.tools.map((tool) => (
            <div
              key={tool.id}
              className="bg-blue-900/20 border border-blue-700/50 rounded p-2 text-xs"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="font-semibold text-blue-300">{tool.name}</span>
                <span className="text-gray-500">#{tool.id.slice(0, 8)}</span>
              </div>
              <div className="text-gray-400 font-mono text-[10px] overflow-x-auto">
                <pre className="whitespace-pre-wrap break-all">{tool.arguments}</pre>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
