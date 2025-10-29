/**
 * Agent configuration constants for the research application.
 *
 * Defines display properties and metadata for each agent in the research team.
 */

import { AgentConfig, AgentName } from '../types'

/**
 * Agent configurations matching the research team setup.
 */
export const AGENT_CONFIGS: Record<AgentName, AgentConfig> = {
  [AgentName.USER_PROXY]: {
    name: AgentName.USER_PROXY,
    displayName: 'User Proxy',
    color: 'rgba(147, 51, 234, 0.4)', // purple
    description: 'Human admin who can approve plans and provide guidance',
  },
  [AgentName.DEVELOPER]: {
    name: AgentName.DEVELOPER,
    displayName: 'Developer',
    color: 'rgba(59, 130, 246, 0.4)', // blue
    description: 'AI developer that writes code to solve tasks',
  },
  [AgentName.PLANNER]: {
    name: AgentName.PLANNER,
    displayName: 'Planner',
    color: 'rgba(236, 72, 153, 0.4)', // pink
    description: 'AI planner that creates detailed research plans',
  },
  [AgentName.EXECUTOR]: {
    name: AgentName.EXECUTOR,
    displayName: 'Executor',
    color: 'rgba(34, 197, 94, 0.4)', // green
    description: 'Executes code blocks and reports results',
  },
  [AgentName.QUALITY_ASSURANCE]: {
    name: AgentName.QUALITY_ASSURANCE,
    displayName: 'Quality Assurance',
    color: 'rgba(251, 146, 60, 0.4)', // orange
    description: 'AI QA that reviews plans and code for errors',
  },
  [AgentName.WEB_SEARCH_AGENT]: {
    name: AgentName.WEB_SEARCH_AGENT,
    displayName: 'Web Search',
    color: 'rgba(20, 184, 166, 0.4)', // teal
    description: 'Searches the web for information',
  },
  [AgentName.REPORT_WRITER]: {
    name: AgentName.REPORT_WRITER,
    displayName: 'Report Writer',
    color: 'rgba(139, 92, 246, 0.4)', // indigo
    description: 'Writes final research reports',
  },
  [AgentName.USER]: {
    name: AgentName.USER,
    displayName: 'User',
    color: 'rgba(255, 255, 255, 0.4)', // white
    description: 'Human user controlling the research',
  },
  [AgentName.SYSTEM]: {
    name: AgentName.SYSTEM,
    displayName: 'System',
    color: 'rgba(156, 163, 175, 0.4)', // gray
    description: 'System messages and initialization',
  },
}

/**
 * List of research participant agent names (excludes User and System).
 */
export const RESEARCH_PARTICIPANTS: AgentName[] = [
  AgentName.USER_PROXY,
  AgentName.DEVELOPER,
  AgentName.PLANNER,
  AgentName.EXECUTOR,
  AgentName.QUALITY_ASSURANCE,
  AgentName.WEB_SEARCH_AGENT,
  AgentName.REPORT_WRITER,
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
