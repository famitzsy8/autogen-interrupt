/**
 * Configuration form component.
 *
 * Allows users to input the initial task and optionally customize the selector prompt
 * before starting a conversation session.
 */

import React, { useState } from 'react'
import type { RunConfig, Agent } from '../types'
import { MessageType } from '../types'
import { getOrCreateSessionId } from '../utils/session'
import { AgentSelector } from './AgentSelector'

interface ConfigFormProps {
  onSubmit: (config: RunConfig) => void
  isLoading?: boolean
  agentTeamNames: string[] | null
  participantNames: string[] | null
  agentDetails: Agent[] | null
}

// Company-Bill investigation pairs
interface CompanyBillPair {
  id: string
  company_name: string
  bill_name: string
  congress: string
  label: string
}

const COMPANY_BILL_PAIRS: CompanyBillPair[] = [
  {
    id: 'exxonmobil-s1593-116th',
    company_name: 'ExxonMobil',
    bill_name: 'S.1593',
    congress: '116th',
    label: 'ExxonMobil - S.1593 (116th Congress)'
  }
]

export function ConfigForm({
  onSubmit,
  isLoading = false,
  agentTeamNames,
  participantNames,
  agentDetails,
}: ConfigFormProps): React.ReactElement {
  const [topic, setTopic] = useState('')
  const [selectedPairId, setSelectedPairId] = useState<string>(COMPANY_BILL_PAIRS[0].id)

  const normalizedTeamNames = agentTeamNames?.map((name) => name.toLowerCase()) ?? []
  const isCongressTeam = normalizedTeamNames.some((name) => name.includes('congress'))
  const isResearchTeam = normalizedTeamNames.some((name) => name.includes('research'))

  const showOnlyResearchFields = isResearchTeam && !isCongressTeam
  const showCompanyBillField = isCongressTeam || (!isCongressTeam && !isResearchTeam)
  const showTaskField = isResearchTeam || (!isResearchTeam && !isCongressTeam)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!agentTeamNames || agentTeamNames.length === 0) {
      alert('Waiting for agent team names from backend...')
      return
    }

    // Find the selected company-bill pair
    const selectedPair = COMPANY_BILL_PAIRS.find(pair => pair.id === selectedPairId)

    const config: RunConfig = {
      type: MessageType.START_RUN,
      session_id: getOrCreateSessionId(),
      initial_topic: showTaskField ? (topic.trim() || undefined) : undefined,
      ...(showCompanyBillField && selectedPair
        ? {
            company_name: selectedPair.company_name,
            bill_name: selectedPair.bill_name,
            congress: selectedPair.congress,
          }
        : {}),
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
          <h1 className="text-4xl font-bold mb-2">Agent Team</h1>
          <p className="text-gray-400">Configure your task</p>
        </div>

        {/* Agent Team Names Display */}
        {agentTeamNames && agentTeamNames.length > 0 ? (
          <div className="bg-green-900/30 border border-green-700 rounded-lg px-4 py-3 flex flex-wrap items-center gap-2">
            <span className="text-green-400 font-semibold">✓ Connected to team:</span>
            <div className="flex gap-2 flex-wrap">
              {agentTeamNames.map((name) => (
                <span
                  key={name}
                  className="bg-green-800/50 text-green-300 px-3 py-1 rounded-md text-sm"
                >
                  {name}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-4">
            <span className="text-yellow-400">⏳ Waiting for agent team names from backend...</span>
          </div>
        )}

        {/* Participant Names Display */}
        {participantNames && participantNames.length > 0 && (
          <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-blue-400 font-semibold">👥 Team Members:</span>
            </div>
            <div className="flex gap-2 flex-wrap">
              {participantNames.map((name) => (
                <span
                  key={name}
                  className="bg-blue-800/50 text-blue-300 px-3 py-1 rounded-md text-sm"
                >
                  {name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Agent Details Selector */}
        <AgentSelector agents={agentDetails} />

        {/* Company-Bill Investigation Pair Dropdown */}
        {showCompanyBillField && (
          <div>
            <label className="block text-sm font-semibold mb-2">
              Company-Bill Investigation Pair
            </label>
            <select
              value={selectedPairId}
              onChange={(e) => setSelectedPairId(e.target.value)}
              className="w-full bg-gray-900 text-dark-text border border-gray-600 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
            >
              {COMPANY_BILL_PAIRS.map((pair) => (
                <option key={pair.id} value={pair.id}>
                  {pair.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Select the company and bill to investigate
            </p>
          </div>
        )}

        {/* Task Input */}
        {showTaskField && (
          <div>
            <label className="block text-sm font-semibold mb-2">
              {showOnlyResearchFields ? 'Task / Initial Prompt' : 'Task / Initial Prompt (optional)'}
            </label>
            <textarea
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="What would you like the AI agents to work on? Leave blank to use the backend's default task."
              className="w-full bg-gray-900 text-dark-text border border-gray-600 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-32"
              disabled={isLoading}
            />
            <p className="text-xs text-gray-500 mt-1">
              If empty, the backend's default task will be used
            </p>
          </div>
        )}

        {/* Buttons */}
        <div className="flex gap-3 pt-6">
          <button
            type="submit"
            disabled={isLoading || !agentTeamNames || agentTeamNames.length === 0}
            className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition"
          >
            {isLoading ? '🔄 Connecting...' : agentTeamNames && agentTeamNames.length > 0 ? '▶ Start' : '⏳ Waiting...'}
          </button>
        </div>
      </form>
    </div>
  )
}
