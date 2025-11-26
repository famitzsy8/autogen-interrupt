/**
 * Configuration form component.
 *
 * Allows users to input the initial task and optionally customize the selector prompt
 * before starting a conversation session.
 */

import React, { useState, useEffect, useRef } from 'react'
import type { RunConfig, Agent, AnalysisComponent, RunStartConfirmed } from '../types'
import { MessageType } from '../types'
import { getOrCreateSessionId } from '../utils/session'
import { AgentSelector } from './AgentSelector'
import { ComponentReviewModal } from './ComponentReviewModal'
import {
  useGeneratedComponents,
  useIsGeneratingComponents,
  useComponentGenerationActions,
} from '../hooks/useStore'

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

// Generate congress.gov URL from bill name and congress number
function getCongressGovUrl(billName: string, congress: string): string {
  // Extract congress number (e.g., "116th" -> "116th")
  const congressNum = congress.toLowerCase().replace('th', 'th')

  // Parse bill name to get type and number
  // Examples: "S.1593" -> senate-bill/1593, "H.R.1044" -> house-bill/1044
  // "H.J.Res.129" -> house-joint-resolution/129, "S.Con.Res.14" -> senate-concurrent-resolution/14
  const billUpper = billName.toUpperCase()

  let billType: string
  let billNumber: string

  if (billUpper.startsWith('H.J.RES.')) {
    billType = 'house-joint-resolution'
    billNumber = billName.replace(/H\.J\.Res\./i, '')
  } else if (billUpper.startsWith('S.J.RES.')) {
    billType = 'senate-joint-resolution'
    billNumber = billName.replace(/S\.J\.Res\./i, '')
  } else if (billUpper.startsWith('H.CON.RES.')) {
    billType = 'house-concurrent-resolution'
    billNumber = billName.replace(/H\.Con\.Res\./i, '')
  } else if (billUpper.startsWith('S.CON.RES.')) {
    billType = 'senate-concurrent-resolution'
    billNumber = billName.replace(/S\.Con\.Res\./i, '')
  } else if (billUpper.startsWith('H.RES.')) {
    billType = 'house-resolution'
    billNumber = billName.replace(/H\.Res\./i, '')
  } else if (billUpper.startsWith('S.RES.')) {
    billType = 'senate-resolution'
    billNumber = billName.replace(/S\.Res\./i, '')
  } else if (billUpper.startsWith('H.R.')) {
    billType = 'house-bill'
    billNumber = billName.replace(/H\.R\./i, '')
  } else if (billUpper.startsWith('S.')) {
    billType = 'senate-bill'
    billNumber = billName.replace(/S\./i, '')
  } else {
    // Fallback - shouldn't happen with valid data
    return ''
  }

  return `https://www.congress.gov/bill/${congressNum}-congress/${billType}/${billNumber}`
}

const COMPANY_BILL_PAIRS: CompanyBillPair[] = [
  // ExxonMobil
  {
    id: 'exxonmobil-s1593-116th',
    company_name: 'ExxonMobil',
    bill_name: 'S.1593',
    congress: '116th',
    label: 'ExxonMobil - S.1593 (116th Congress)',
  },
  // Apple
  {
    id: 'apple-s3933-116th',
    company_name: 'APPLE',
    bill_name: 'S.3933',
    congress: '116th',
    label: 'APPLE - S.3933 (116th Congress)',
  },
  {
    id: 'apple-hr1044-116th',
    company_name: 'APPLE INC',
    bill_name: 'H.R.1044',
    congress: '116th',
    label: 'APPLE INC - H.R.1044 (116th Congress)',
  },
  {
    id: 'apple-hr1494-115th',
    company_name: 'APPLE INC',
    bill_name: 'H.R.1494',
    congress: '115th',
    label: 'APPLE INC - H.R.1494 (115th Congress)',
  },
  {
    id: 'apple-hr6210-116th',
    company_name: 'APPLE INC',
    bill_name: 'H.R.6210',
    congress: '116th',
    label: 'APPLE INC - H.R.6210 (116th Congress)',
  },
  {
    id: 'apple-s1336-117th',
    company_name: 'APPLE INC',
    bill_name: 'S.1336',
    congress: '117th',
    label: 'APPLE INC - S.1336 (117th Congress)',
  },
  {
    id: 'apple-s3398-116th',
    company_name: 'APPLE INC',
    bill_name: 'S.3398',
    congress: '116th',
    label: 'APPLE INC - S.3398 (116th Congress)',
  },
  {
    id: 'apple-s4066-116th',
    company_name: 'APPLE INC',
    bill_name: 'S.4066',
    congress: '116th',
    label: 'APPLE INC - S.4066 (116th Congress)',
  },
  {
    id: 'apple-s4433-117th',
    company_name: 'APPLE INC',
    bill_name: 'S.4433',
    congress: '117th',
    label: 'APPLE INC - S.4433 (117th Congress)',
  },
  {
    id: 'apple-s5020-116th',
    company_name: 'APPLE INC',
    bill_name: 'S.5020',
    congress: '116th',
    label: 'APPLE INC - S.5020 (116th Congress)',
  },
  // AT&T
  {
    id: 'att-hr3347-115th',
    company_name: 'AT&T SERVICES',
    bill_name: 'H.R.3347',
    congress: '115th',
    label: 'AT&T SERVICES - H.R.3347 (115th Congress)',
  },
  {
    id: 'att-hr588-115th',
    company_name: 'AT&T SERVICES',
    bill_name: 'H.R.588',
    congress: '115th',
    label: 'AT&T SERVICES - H.R.588 (115th Congress)',
  },
  {
    id: 'att-s102-115th',
    company_name: 'AT&T SERVICES',
    bill_name: 'S.102',
    congress: '115th',
    label: 'AT&T SERVICES - S.102 (115th Congress)',
  },
  {
    id: 'att-hjres129-115th',
    company_name: 'AT&T SERVICES INC',
    bill_name: 'H.J.Res.129',
    congress: '115th',
    label: 'AT&T SERVICES INC - H.J.Res.129 (115th Congress)',
  },
  {
    id: 'att-hr346-115th',
    company_name: 'AT&T SERVICES INC',
    bill_name: 'H.R.346',
    congress: '115th',
    label: 'AT&T SERVICES INC - H.R.346 (115th Congress)',
  },
  {
    id: 'att-hr4682-115th',
    company_name: 'AT&T SERVICES INC',
    bill_name: 'H.R.4682',
    congress: '115th',
    label: 'AT&T SERVICES INC - H.R.4682 (115th Congress)',
  },
  {
    id: 'att-hr5117-114th',
    company_name: 'AT&T SERVICES INC',
    bill_name: 'H.R.5117',
    congress: '114th',
    label: 'AT&T SERVICES INC - H.R.5117 (114th Congress)',
  },
  {
    id: 'att-hr5496-115th',
    company_name: 'AT&T SERVICES INC',
    bill_name: 'H.R.5496',
    congress: '115th',
    label: 'AT&T SERVICES INC - H.R.5496 (115th Congress)',
  },
  {
    id: 'att-s19-115th',
    company_name: 'AT&T SERVICES INC',
    bill_name: 'S.19',
    congress: '115th',
    label: 'AT&T SERVICES INC - S.19 (115th Congress)',
  },
  {
    id: 'att-s2555-114th',
    company_name: 'AT&T SERVICES INC',
    bill_name: 'S.2555',
    congress: '114th',
    label: 'AT&T SERVICES INC - S.2555 (114th Congress)',
  },
  // Shell Oil Company
  {
    id: 'shell-hr2184-117th',
    company_name: 'SHELL OIL COMPANY',
    bill_name: 'H.R.2184',
    congress: '117th',
    label: 'SHELL OIL COMPANY - H.R.2184 (117th Congress)',
  },
  {
    id: 'shell-hr5376-117th',
    company_name: 'SHELL OIL COMPANY',
    bill_name: 'H.R.5376',
    congress: '117th',
    label: 'SHELL OIL COMPANY - H.R.5376 (117th Congress)',
  },
  {
    id: 'shell-s1298-117th',
    company_name: 'SHELL OIL COMPANY',
    bill_name: 'S.1298',
    congress: '117th',
    label: 'SHELL OIL COMPANY - S.1298 (117th Congress)',
  },
  {
    id: 'shell-s2118-117th',
    company_name: 'SHELL OIL COMPANY',
    bill_name: 'S.2118',
    congress: '117th',
    label: 'SHELL OIL COMPANY - S.2118 (117th Congress)',
  },
  {
    id: 'shell-s423-116th',
    company_name: 'SHELL OIL COMPANY',
    bill_name: 'S.423',
    congress: '116th',
    label: 'SHELL OIL COMPANY - S.423 (116th Congress)',
  },
  {
    id: 'shell-sconres14-117th',
    company_name: 'SHELL OIL COMPANY',
    bill_name: 'S.Con.Res.14',
    congress: '117th',
    label: 'SHELL OIL COMPANY - S.Con.Res.14 (117th Congress)',
  },
  {
    id: 'shell-hjres31-116th',
    company_name: 'SHELL USA, INC.',
    bill_name: 'H.J.Res.31',
    congress: '116th',
    label: 'SHELL USA, INC. - H.J.Res.31 (116th Congress)',
  },
  {
    id: 'shell-hr133-116th',
    company_name: 'SHELL USA, INC.',
    bill_name: 'H.R.133',
    congress: '116th',
    label: 'SHELL USA, INC. - H.R.133 (116th Congress)',
  },
  {
    id: 'shell-hr1512-117th',
    company_name: 'SHELL USA, INC.',
    bill_name: 'H.R.1512',
    congress: '117th',
    label: 'SHELL USA, INC. - H.R.1512 (117th Congress)',
  },
  {
    id: 'shell-hr1848-117th',
    company_name: 'SHELL USA, INC.',
    bill_name: 'H.R.1848',
    congress: '117th',
    label: 'SHELL USA, INC. - H.R.1848 (117th Congress)',
  },
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
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const [analysisPrompt, setAnalysisPrompt] = useState<string>('')
  const [triggerThreshold] = useState<number>(8)

  // Walkthrough stage: 1 = agents, 2 = task/dropdown, 3 = watchlist + start
  const [walkthroughStage, setWalkthroughStage] = useState<1 | 2 | 3>(1)

  // Refs for smooth scrolling to each stage
  const stage2Ref = useRef<HTMLDivElement>(null)
  const stage3Ref = useRef<HTMLDivElement>(null)

  // Scroll to the new stage when it appears
  useEffect(() => {
    const scrollTimeout = setTimeout(() => {
      if (walkthroughStage === 2 && stage2Ref.current) {
        stage2Ref.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
      } else if (walkthroughStage === 3 && stage3Ref.current) {
        stage3Ref.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }, 50) // Small delay to let the DOM update first

    return () => clearTimeout(scrollTimeout)
  }, [walkthroughStage])

  // Component generation state
  const [showReviewModal, setShowReviewModal] = useState(false)
  const [configData, setConfigData] = useState<{
    initial_topic?: string
    company_name?: string
    bill_name?: string
    congress?: string
  } | null>(null)

  const generatedComponents = useGeneratedComponents()
  const isGeneratingComponents = useIsGeneratingComponents()
  const { sendComponentGenerationRequest, sendRunStartConfirmed } = useComponentGenerationActions()

  // Show modal when components are generated
  useEffect(() => {
    if (generatedComponents !== null && configData !== null) {
      setShowReviewModal(true)
    }
  }, [generatedComponents, configData])

  const normalizedTeamNames = agentTeamNames?.map((name) => name.toLowerCase()) ?? []
  const isCongressTeam = normalizedTeamNames.some((name) => name.includes('congress'))
  const isResearchTeam = normalizedTeamNames.some((name) => name.includes('research'))

  // Congress team: show company-bill dropdown + things to watch out for
  // Research team: show task/initial prompt + things to watch out for
  const showCompanyBillField = isCongressTeam
  const showTaskField = isResearchTeam

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!agentTeamNames || agentTeamNames.length === 0) {
      alert('Waiting for agent team names from backend...')
      return
    }

    // Find the selected company-bill pair
    const selectedPair = COMPANY_BILL_PAIRS.find(pair => pair.id === selectedPairId)

    // Store config data for later use
    const data = {
      initial_topic: showTaskField ? (topic.trim() || undefined) : undefined,
      ...(showCompanyBillField && selectedPair
        ? {
          company_name: selectedPair.company_name,
          bill_name: selectedPair.bill_name,
          congress: selectedPair.congress,
        }
        : {}),
    }
    setConfigData(data)

    // If analysis prompt provided, request component generation first
    if (analysisPrompt.trim()) {
      sendComponentGenerationRequest(analysisPrompt.trim(), triggerThreshold)
    } else {
      // No analysis - send old-style RunConfig directly
      const config: RunConfig = {
        type: MessageType.START_RUN,
        session_id: getOrCreateSessionId(),
        ...data,
        timestamp: new Date().toISOString(),
      }
      onSubmit(config)
    }
  }

  const handleComponentsApproved = (approvedComponents: AnalysisComponent[]) => {
    if (!configData) return

    const config: RunStartConfirmed = {
      type: MessageType.RUN_START_CONFIRMED,
      session_id: getOrCreateSessionId(),
      ...configData,
      approved_components: approvedComponents,
      trigger_threshold: triggerThreshold,
      timestamp: new Date().toISOString(),
    }

    sendRunStartConfirmed(config)
    setShowReviewModal(false)
    // Trigger onSubmit to mark as configured in App
    onSubmit(config as unknown as RunConfig)
  }

  const handleCancelReview = () => {
    setShowReviewModal(false)
    setConfigData(null)
  }

  return (
    <div className="min-h-screen bg-dark-bg text-dark-text flex items-center justify-center p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-2xl bg-dark-border rounded-lg p-8 space-y-6"
      >
        {/* Stage 1: Title + Participants + Agent Selector */}
        <div>
          <h1 className="text-4xl font-bold mb-2">Welcome to my Bachelor thesis!</h1>
        </div>

        {/* Participant Names Display */}
        {participantNames && participantNames.length > 0 && (
          <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-blue-400 font-semibold">Team Members:</span>
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
        <AgentSelector
          agents={agentDetails}
          selectedAgent={selectedAgent}
          onSelectAgent={setSelectedAgent}
        />

        {/* Stage 1 Button: What are these agents about to do? */}
        {walkthroughStage === 1 && (
          <button
            type="button"
            onClick={() => setWalkthroughStage(2)}
            className="w-full bg-red-900/40 hover:bg-red-900/60 border border-red-700 text-red-300 font-semibold py-3 px-4 rounded-lg transition"
          >
            What are these agents about to do?
          </button>
        )}

        {/* Stage 2: Company-Bill Dropdown or Task Input */}
        {walkthroughStage >= 2 && (
          <div ref={stage2Ref}>
            {/* Company-Bill Investigation Pair Dropdown */}
            {showCompanyBillField && (
              <div>
                <h2 className="text-gray-300 mb-4">
                  The agents above will investigate the most aligned and most opposed politicians to a company's likely position on a bill. In order to do this, they can call "tools" that retrieve information from the U.S. Congress website. You will guide and supervise them :)
                </h2>
                <label className="block text-sm font-semibold mb-2">
                  Choose the Company and the Bill it lobbied for!
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

                {/* Congress.gov link for selected bill */}
                {(() => {
                  const selectedPair = COMPANY_BILL_PAIRS.find(p => p.id === selectedPairId)
                  if (!selectedPair) return null
                  const congressUrl = getCongressGovUrl(selectedPair.bill_name, selectedPair.congress)
                  if (!congressUrl) return null
                  return (
                    <div className="mt-3 p-3 bg-blue-900/20 border border-blue-700/50 rounded-lg">
                      <a
                        href={congressUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-2 transition-colors"
                      >
                        <span>In case you need a refresh on what {selectedPair.bill_name} is about, check it out on the Congress website!</span>
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                          <polyline points="15 3 21 3 21 9" />
                          <line x1="10" y1="14" x2="21" y2="3" />
                        </svg>
                      </a>
                    </div>
                  )
                })()}
              </div>
            )}

            {/* Task Input */}
            {showTaskField && (
              <div>
                <label className="block text-sm font-semibold mb-2">
                  What do you want to do a deep dive on?
                </label>
                <textarea
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="What would you like the AI agents to work on? Leave blank to use the backend's default task."
                  className="w-full bg-gray-900 text-dark-text border border-gray-600 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-32"
                  disabled={isLoading}
                />
              </div>
            )}

            {/* Stage 2 Button: And how am I involved? */}
            {walkthroughStage === 2 && (
              <button
                type="button"
                onClick={() => setWalkthroughStage(3)}
                className="w-full bg-red-900/40 hover:bg-red-900/60 border border-red-700 text-red-300 font-semibold py-3 px-4 rounded-lg transition mt-4"
              >
                And how am I involved?
              </button>
            )}
          </div>
        )}

        {/* Stage 3: Analysis Watchlist + Start Button */}
        {walkthroughStage >= 3 && (
          <div ref={stage3Ref} className="space-y-6">
            {/* Explanation text */}
            <p className="text-gray-300">
              You can interrupt these agents and send messages to them. But most importantly: You can specify things you want to watch out for, and the agents will automatically involve you when they happen!
            </p>

            {/* Analysis Watchlist Section */}
            <div className="border border-gray-700 rounded-lg p-4 bg-gray-900/50">
              <h3 className="text-base font-semibold mb-2">Things You Want to Watch Out For</h3>

              <div className="mb-4">
                <textarea
                  id="analysis-prompt"
                  value={analysisPrompt}
                  onChange={(e) => setAnalysisPrompt(e.target.value)}
                  placeholder="e.g., Watch for hallucinated committee members or incorrect geographic information..."
                  rows={3}
                  className="w-full bg-gray-900 text-dark-text border border-gray-600 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                  disabled={isLoading}
                />
              </div>

            </div>

            {/* Start Button */}
            <div className="flex gap-3 pt-6">
              <button
                type="submit"
                disabled={isLoading || isGeneratingComponents || !agentTeamNames || agentTeamNames.length === 0}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition"
              >
                {isGeneratingComponents
                  ? 'Generating Components...'
                  : isLoading
                    ? 'Connecting...'
                    : agentTeamNames && agentTeamNames.length > 0
                      ? 'Start'
                      : 'Waiting...'}
              </button>
            </div>
          </div>
        )}
      </form>

      {/* Component Review Modal */}
      {showReviewModal && generatedComponents !== null && (
        <ComponentReviewModal
          components={generatedComponents}
          trigger_threshold={triggerThreshold}
          onApprove={handleComponentsApproved}
          onCancel={handleCancelReview}
          isGenerating={isGeneratingComponents}
        />
      )}
    </div>
  )
}
