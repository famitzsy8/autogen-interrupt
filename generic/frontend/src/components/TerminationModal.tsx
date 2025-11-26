/**
 * Termination Modal Component
 *
 * Displays a modal when the agent run is terminated by user request.
 * Shows the final research state, tool call facts, and last agent message.
 */

import { CheckCircle, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useTerminationData, useTerminationActions } from '../hooks/useStore'
import { AgentBadge } from './AgentBadge'
import './StateDisplay/StateDisplay.css'

export const TerminationModal: React.FC = () => {
  const terminationData = useTerminationData()
  const { clearTerminationData } = useTerminationActions()

  // Don't render if no termination data
  if (!terminationData) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      {/* Modal card */}
      <div
        className="relative bg-gray-800 border border-gray-600 rounded-lg shadow-2xl max-w-3xl w-full mx-4 max-h-[85vh] overflow-hidden flex flex-col"
        role="dialog"
        aria-labelledby="termination-modal-title"
      >
        {/* Header bar */}
        <div className="bg-gray-700 px-4 py-3 rounded-t-lg border-b border-gray-600 flex items-center justify-between flex-shrink-0">
          <h3
            id="termination-modal-title"
            className="text-base font-semibold text-gray-200 flex items-center gap-2"
          >
            <CheckCircle className="w-5 h-5 text-green-400" />
            <span>Run Terminated</span>
          </h3>
          <button
            onClick={clearTerminationData}
            className="p-1 text-gray-400 hover:text-gray-200 hover:bg-gray-600 rounded transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="p-4 space-y-4 overflow-y-auto flex-1">
          {/* Success Message */}
          <div className="flex gap-3 p-3 bg-green-950/40 rounded-lg border border-green-700/50">
            <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <strong className="text-green-300 text-sm font-semibold block mb-1">
                Run Successfully Terminated
              </strong>
              <p className="text-xs text-gray-300">
                The agent run has been terminated. Below is the final research state and findings.
              </p>
            </div>
          </div>

          {/* Last Message Section */}
          {terminationData.last_message_content && (
            <div className="rounded-lg border border-gray-600/50 bg-gray-900/30 overflow-hidden">
              <div className="px-4 py-2 bg-gray-700/50 border-b border-gray-600/50 flex items-center gap-2">
                <span className="text-sm font-semibold text-gray-200">Last Message</span>
                {terminationData.last_message_source && (
                  <AgentBadge agentName={terminationData.last_message_source} size="sm" />
                )}
              </div>
              <div className="p-4 text-sm text-gray-300 markdown-content">
                <ReactMarkdown>{terminationData.last_message_content}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* State of Run Section */}
          {terminationData.state_of_run && (
            <div className="rounded-lg border border-gray-600/50 bg-gray-900/30 overflow-hidden">
              <div className="px-4 py-2 bg-gray-700/50 border-b border-gray-600/50">
                <span className="text-sm font-semibold text-gray-200">Research State</span>
              </div>
              <div className="p-4 text-sm text-gray-300 markdown-content">
                <ReactMarkdown>{terminationData.state_of_run}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* Tool Call Facts Section */}
          {terminationData.tool_call_facts && (
            <div className="rounded-lg border border-gray-600/50 bg-gray-900/30 overflow-hidden">
              <div className="px-4 py-2 bg-gray-700/50 border-b border-gray-600/50">
                <span className="text-sm font-semibold text-gray-200">Verified Facts</span>
              </div>
              <div className="p-4 text-sm text-gray-300 markdown-content">
                <ReactMarkdown>{terminationData.tool_call_facts}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 bg-gray-700/50 border-t border-gray-600 flex justify-end flex-shrink-0">
          <button
            onClick={clearTerminationData}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default TerminationModal
