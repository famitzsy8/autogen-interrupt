/**
 * ToolExecutionItem displays tool execution results in a collapsible format.
 * Shows the results of tool calls with success/failure status.
 */

import React, { useState } from 'react'
import { ChevronDown, ChevronRight, CheckCircle, XCircle } from 'lucide-react'
import type { ToolExecution } from '../../types'

interface ToolExecutionItemProps {
  toolExecution: ToolExecution
}

export function ToolExecutionItem({ toolExecution }: ToolExecutionItemProps): React.ReactElement {
  const [isExpanded, setIsExpanded] = useState(false)

  const successCount = toolExecution.results.filter((r) => r.success).length
  const failureCount = toolExecution.results.length - successCount

  return (
    <div className="mb-2 pl-5">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-xs text-green-400 hover:text-green-300 transition-colors"
      >
        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <CheckCircle size={14} />
        <span className="font-medium">
          Tool results: {successCount} success{successCount !== 1 ? 'es' : ''}{' '}
          {failureCount > 0 && `/ ${failureCount} failure${failureCount !== 1 ? 's' : ''}`}
        </span>
      </button>

      {isExpanded && (
        <div className="mt-2 ml-6 space-y-2">
          {toolExecution.results.map((result) => (
            <div
              key={result.tool_call_id}
              className={`border rounded p-2 text-xs ${
                result.success
                  ? 'bg-green-900/20 border-green-700/50'
                  : 'bg-red-900/20 border-red-700/50'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                {result.success ? (
                  <CheckCircle size={12} className="text-green-400" />
                ) : (
                  <XCircle size={12} className="text-red-400" />
                )}
                <span className={`font-semibold ${result.success ? 'text-green-300' : 'text-red-300'}`}>
                  {result.tool_name}
                </span>
                <span className="text-gray-500">#{result.tool_call_id.slice(0, 8)}</span>
              </div>
              {result.result && (
                <div className="text-gray-400 font-mono text-[10px] overflow-x-auto max-h-32 overflow-y-auto">
                  <pre className="whitespace-pre-wrap break-all">{result.result}</pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
