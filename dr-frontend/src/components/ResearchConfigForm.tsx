/**
 * Research configuration form component.
 *
 * Allows users to input the research topic and optionally customize the selector prompt
 * before starting a research session.
 */

import React, { useState } from 'react'
import type { ResearchConfig } from '../types'

interface ResearchConfigFormProps {
  onSubmit: (config: ResearchConfig) => void
  isLoading?: boolean
}

export function ResearchConfigForm({
  onSubmit,
  isLoading = false,
}: ResearchConfigFormProps): React.ReactElement {
  const [topic, setTopic] = useState('')
  const [selectorPrompt, setSelectorPrompt] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!topic.trim()) {
      alert('Please enter a research topic')
      return
    }

    const config: ResearchConfig = {
      type: 'start_research',
      initial_topic: topic.trim(),
      selector_prompt: selectorPrompt.trim() || undefined,
      timestamp: new Date().toISOString(),
    }

    onSubmit(config)
  }

  return (
    <div className="min-h-screen bg-dark-bg text-dark-text flex items-center justify-center p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-2xl bg-dark-border rounded-lg p-8 space-y-6"
      >
        <div>
          <h1 className="text-4xl font-bold mb-2">Deep Research</h1>
          <p className="text-gray-400">Configure your research task</p>
        </div>

        {/* Research Topic */}
        <div>
          <label className="block text-sm font-semibold mb-2">
            Research Topic / Task *
          </label>
          <textarea
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="What would you like the AI agents to research? (e.g., 'Find key trends in machine learning for 2024')"
            className="w-full bg-gray-900 text-dark-text border border-gray-600 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-32"
            disabled={isLoading}
          />
          <p className="text-xs text-gray-500 mt-1">
            This becomes the initial task for all agents
          </p>
        </div>

        {/* Advanced Toggle */}
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          disabled={isLoading}
          className="text-sm text-blue-400 hover:text-blue-300 underline disabled:text-gray-500"
        >
          {showAdvanced ? '▼' : '▶'} Advanced Settings
        </button>

        {/* Selector Prompt (Advanced) */}
        {showAdvanced && (
          <div>
            <label className="block text-sm font-semibold mb-2">
              Selector Prompt (optional)
            </label>
            <textarea
              value={selectorPrompt}
              onChange={(e) => setSelectorPrompt(e.target.value)}
              placeholder="Control how agents are selected to speak. Leave blank for default agent selection logic."
              className="w-full bg-gray-900 text-dark-text border border-gray-600 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-24"
              disabled={isLoading}
            />
            <p className="text-xs text-gray-500 mt-1">
              Advanced: Custom prompt template for the selector model
            </p>
          </div>
        )}

        {/* Buttons */}
        <div className="flex gap-3 pt-6">
          <button
            type="submit"
            disabled={!topic.trim() || isLoading}
            className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition"
          >
            {isLoading ? '🔄 Starting Research...' : '▶ Start Research'}
          </button>
        </div>
      </form>
    </div>
  )
}
