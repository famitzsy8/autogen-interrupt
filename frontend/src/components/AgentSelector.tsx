/**
 * Agent selector component for displaying and selecting through available agents.
 *
 * Displays a clickable interface to browse through agents with their names and short summaries.
 */

import { useEffect } from 'react'
import type { Agent } from '../types'
import { AgentBadge } from './AgentBadge'

interface AgentSelectorProps {
  agents: Agent[] | null
  selectedAgent: string | null
  onSelectAgent: (agent: string | null) => void
  disabled?: boolean
}

export function AgentSelector({ agents, selectedAgent, onSelectAgent, disabled }: AgentSelectorProps) {
  // Filter out "User" agents - we can't send directed messages to ourselves
  const filteredAgents = agents?.filter(agent => {
    const name = agent.name.toLowerCase()
    return name !== 'user' && name !== 'you' && !name.includes('user_proxy') && !name.includes('userproxy')
  }) || []

  if (filteredAgents.length === 0) {
    return (
      <div className="bg-dark-surface border border-dark-border rounded-lg p-4">
        <span className="text-dark-text-secondary">⏳ Loading agent details...</span>
      </div>
    )
  }

  // Find index of selected agent, default to 0
  const selectedIndex = selectedAgent
    ? filteredAgents.findIndex(a => a.name === selectedAgent)
    : 0

  const effectiveIndex = selectedIndex === -1 ? 0 : selectedIndex
  const currentAgent = filteredAgents[effectiveIndex]

  const handlePrevious = () => {
    const newIndex = effectiveIndex === 0 ? filteredAgents.length - 1 : effectiveIndex - 1
    onSelectAgent(filteredAgents[newIndex].name)
  }

  const handleNext = () => {
    const newIndex = effectiveIndex === filteredAgents.length - 1 ? 0 : effectiveIndex + 1
    onSelectAgent(filteredAgents[newIndex].name)
  }

  // Initialize selection if needed
  useEffect(() => {
    if (!selectedAgent && filteredAgents.length > 0) {
      onSelectAgent(filteredAgents[0].name)
    }
  }, [filteredAgents, selectedAgent, onSelectAgent])

  return (
    <div className={`bg-dark-surface border border-dark-border rounded-lg p-6 space-y-4 ${disabled ? 'opacity-50 pointer-events-none' : ''}`}>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-dark-text font-semibold">Meet the Team!</span>
        <span className="text-dark-text-muted text-sm">
          ({effectiveIndex + 1} of {filteredAgents.length})
        </span>
      </div>

      {/* Agent Display Card */}
      <div className="bg-dark-hover rounded-lg p-5 border border-dark-border">
        <div className="space-y-3">
          <div>
            <AgentBadge
              agentName={currentAgent.name}
              displayName={currentAgent.display_name}
              size="lg"
            />
          </div>
          <p className="text-sm text-dark-text leading-relaxed">
            {currentAgent.summary}
          </p>
        </div>
      </div>

      {/* Navigation Controls */}
      <div className="flex items-center justify-center gap-4">
        <button
          type="button"
          onClick={handlePrevious}
          disabled={disabled}
          className="bg-dark-surface hover:bg-dark-hover text-dark-text p-2 rounded-lg transition disabled:opacity-50"
          aria-label="Previous agent"
        >
          ←
        </button>

        {/* Agent Indicators */}
        <div className="flex gap-1">
          {filteredAgents.map((agent) => (
            <button
              key={agent.name}
              type="button"
              onClick={() => onSelectAgent(agent.name)}
              disabled={disabled}
              className={`w-2 h-2 rounded-full transition ${agent.name === selectedAgent
                ? 'bg-purple-400'
                : 'bg-dark-text-muted hover:bg-dark-text-secondary'
                }`}
              aria-label={`Select ${agent.display_name}`}
              title={agent.display_name}
            />
          ))}
        </div>

        <button
          type="button"
          onClick={handleNext}
          disabled={disabled}
          className="bg-dark-surface hover:bg-dark-hover text-dark-text p-2 rounded-lg transition disabled:opacity-50"
          aria-label="Next agent"
        >
          →
        </button>
      </div>
    </div>
  )
}
