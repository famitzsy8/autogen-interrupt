/**
 * Agent configuration utilities for the generic agent team application.
 *
 * Unlike dr-frontend, we don't hardcode agent names - they come dynamically from the backend.
 */

/**
 * Default color palette for agents.
 * Uses a rotating color scheme for any number of agents.
 */
const AGENT_COLORS = [
  'rgba(147, 51, 234, 0.4)',  // purple
  'rgba(59, 130, 246, 0.4)',   // blue
  'rgba(236, 72, 153, 0.4)',   // pink
  'rgba(34, 197, 94, 0.4)',    // green
  'rgba(251, 146, 60, 0.4)',   // orange
  'rgba(20, 184, 166, 0.4)',   // teal
  'rgba(139, 92, 246, 0.4)',   // indigo
  'rgba(234, 179, 8, 0.4)',    // yellow
  'rgba(239, 68, 68, 0.4)',    // red
  'rgba(168, 85, 247, 0.4)',   // violet
]

/**
 * Special colors for system agents.
 */
const SPECIAL_AGENT_COLORS: Record<string, string> = {
  'You': 'rgba(255, 255, 255, 0.4)',      // white for user
  'User': 'rgba(255, 255, 255, 0.4)',     // white for user
  'System': 'rgba(156, 163, 175, 0.4)',   // gray for system
}

/**
 * Get agent color by name.
 * Uses special colors for system agents, otherwise rotates through color palette.
 */
export function getAgentColor(agentName: string): string {
  // Check for special agents first
  if (SPECIAL_AGENT_COLORS[agentName]) {
    return SPECIAL_AGENT_COLORS[agentName]
  }

  // Generate consistent color based on agent name hash
  const hash = agentName.split('').reduce((acc, char) => {
    return char.charCodeAt(0) + ((acc << 5) - acc)
  }, 0)

  const colorIndex = Math.abs(hash) % AGENT_COLORS.length
  return AGENT_COLORS[colorIndex]
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
