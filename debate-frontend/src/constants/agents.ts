/**
 * Agent configuration constants for the debate application.
 *
 * Defines display properties and metadata for each agent in the debate team.
 */

import { AgentConfig, AgentName } from '../types'

/**
 * Agent configurations matching the debate team setup.
 */
export const AGENT_CONFIGS: Record<AgentName, AgentConfig> = {
  [AgentName.JARA_SUPPORTER]: {
    name: AgentName.JARA_SUPPORTER,
    displayName: 'Jara Supporter',
    color: 'rgba(239, 68, 68, 0.4)', // red
    description: 'Supporter of Daniel Jadue/left-wing candidate',
  },
  [AgentName.KAST_SUPPORTER]: {
    name: AgentName.KAST_SUPPORTER,
    displayName: 'Kast Supporter',
    color: 'rgba(59, 130, 246, 0.4)', // blue
    description: 'Supporter of José Antonio Kast/right-wing candidate',
  },
  [AgentName.NEUTRAL_AGENT]: {
    name: AgentName.NEUTRAL_AGENT,
    displayName: 'Neutral Agent',
    color: 'rgba(168, 85, 247, 0.4)', // purple
    description: 'AI agent that observes and asks clarifying questions',
  },
  [AgentName.MODERATE_LEFT]: {
    name: AgentName.MODERATE_LEFT,
    displayName: 'Moderate Left',
    color: 'rgba(125, 211, 252, 0.4)', // light blue
    description: 'Moderate center-left supporter with pragmatic views',
  },
  [AgentName.MODERATE_RIGHT]: {
    name: AgentName.MODERATE_RIGHT,
    displayName: 'Moderate Right',
    color: 'rgba(251, 146, 60, 0.4)', // orange
    description: 'Moderate center-right supporter with business-friendly views',
  },
  [AgentName.FACT_CHECKER]: {
    name: AgentName.FACT_CHECKER,
    displayName: 'Fact Checker',
    color: 'rgba(34, 197, 94, 0.4)', // green
    description: 'Human fact-checker who verifies claims',
  },
  [AgentName.USER]: {
    name: AgentName.USER,
    displayName: 'User',
    color: 'rgba(255, 255, 255, 0.4)', // white
    description: 'Human user controlling the debate',
  },
  [AgentName.SYSTEM]: {
    name: AgentName.SYSTEM,
    displayName: 'System',
    color: 'rgba(156, 163, 175, 0.4)', // gray
    description: 'System messages and initialization',
  },
}

/**
 * List of debate participant agent names (excludes User, System, and Fact_Checker).
 * Note: Fact_Checker is excluded because users send messages TO agents, not to the fact checker.
 */
export const DEBATE_PARTICIPANTS: AgentName[] = [
  AgentName.JARA_SUPPORTER,
  AgentName.KAST_SUPPORTER,
  AgentName.NEUTRAL_AGENT,
  AgentName.MODERATE_LEFT,
  AgentName.MODERATE_RIGHT,
]

/**
 * Get agent configuration by name.
 * @param agentName - The name of the agent
 * @returns Agent configuration or undefined if not found
 */
export function getAgentConfig(agentName: string): AgentConfig | undefined {
  return AGENT_CONFIGS[agentName as AgentName]
}

/**
 * Get agent color by name.
 * @param agentName - The name of the agent
 * @returns Agent color or default gray if not found
 */
export function getAgentColor(agentName: string): string {
  const config = getAgentConfig(agentName)
  return config?.color ?? 'rgba(156, 163, 175, 0.4)'
}

/**
 * Get agent display name.
 * @param agentName - The name of the agent
 * @returns Agent display name or the original name if not found
 */
export function getAgentDisplayName(agentName: string): string {
  const config = getAgentConfig(agentName)
  return config?.displayName ?? agentName
}
