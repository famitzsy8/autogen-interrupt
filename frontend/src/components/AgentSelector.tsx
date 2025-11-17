/**
 * Agent selector component for displaying and selecting through available agents.
 *
 * Displays a clickable interface to browse through agents with their names and short summaries.
 */

import React, { useState } from 'react'
import type { Agent } from '../types'

interface AgentSelectorProps {
  agents: Agent[] | null
}

export function AgentSelector({ agents }: AgentSelectorProps): React.ReactElement {
  const [selectedIndex, setSelectedIndex] = useState(0)

  if (!agents || agents.length === 0) {
    return (
      <div className="bg-gray-900/30 border border-gray-600 rounded-lg p-4">
        <span className="text-gray-400">⏳ Loading agent details...</span>
      </div>
    )
  }

  const currentAgent = agents[selectedIndex]

  const handlePrevious = () => {
    setSelectedIndex((prev) => (prev === 0 ? agents.length - 1 : prev - 1))
  }

  const handleNext = () => {
    setSelectedIndex((prev) => (prev === agents.length - 1 ? 0 : prev + 1))
  }

  return (
    <div className="bg-purple-900/20 border border-purple-700 rounded-lg p-6 space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-purple-400 font-semibold">These are the Agents in Your Team:</span>
        <span className="text-gray-500 text-sm">
          ({selectedIndex + 1} of {agents.length})
        </span>
      </div>

      {/* Agent Display Card */}
      <div className="bg-gray-900/50 rounded-lg p-5 border border-gray-700/50">
        <div className="space-y-3">
          <div>
            <h3 className="text-lg font-semibold text-purple-300">
              {currentAgent.display_name}
            </h3>
            <p className="text-xs text-gray-500">{currentAgent.name}</p>
          </div>
          <p className="text-sm text-gray-300 leading-relaxed">
            {currentAgent.summary}
          </p>
        </div>
      </div>

      {/* Navigation Controls */}
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={handlePrevious}
          className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 py-2 px-4 rounded-lg transition text-sm font-medium"
        >
          ← Previous
        </button>

        {/* Agent Indicators */}
        <div className="flex gap-1">
          {agents.map((_, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setSelectedIndex(idx)}
              className={`w-2 h-2 rounded-full transition ${
                idx === selectedIndex
                  ? 'bg-purple-400'
                  : 'bg-gray-600 hover:bg-gray-500'
              }`}
              aria-label={`Go to agent ${idx + 1}`}
            />
          ))}
        </div>

        <button
          type="button"
          onClick={handleNext}
          className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 py-2 px-4 rounded-lg transition text-sm font-medium"
        >
          Next →
        </button>
      </div>
    </div>
  )
}
