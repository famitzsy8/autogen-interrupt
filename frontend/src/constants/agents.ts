/**
 * Agent configuration utilities for the generic agent team application.
 *
 * Unlike dr-frontend, we don't hardcode agent names - they come dynamically from the backend.
 * Uses a sequential OrRd (Orange-Red) color scheme for better visual consistency.
 */

import { getAgentColorD3 } from '../utils/colorSchemes'

/**
 * Get agent color by name using D3's interpolateOrRd sequential scheme.
 * Uses special colors for system/user agents, otherwise distributes colors evenly.
 */
export function getAgentColor(agentName: string): string {
  return getAgentColorD3(agentName)
}

/**
 * Get agent display name.
 * Converts snake_case to Title Case for better display.
 */
export function getAgentDisplayName(agentName: string): string {
  // Special cases
  if (agentName === 'You') return 'You'
  if (agentName === 'User') return 'User'
  if (agentName === 'System') return 'System'

  // Convert snake_case or PascalCase to Title Case
  return agentName
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .trim()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}
