/**
 * Color scheme utilities using D3.js d3-scale-chromatic
 *
 * This module provides:
 * 1. Agent colors using interpolateOrRd sequential scheme (evenly distributed)
 * 2. Analysis component colors using sequential schemes
 * 3. Score-based color selection for visualizations
 */

import { interpolateOrRd } from 'd3-scale-chromatic'
import * as d3 from 'd3-scale-chromatic'

/**
 * Sequential color schemes available for analysis components.
 * Each scheme has 9 intensity levels (indices 0-8).
 */
export const SEQUENTIAL_SCHEMES = {
  Blues: d3.schemeBlues,
  Greens: d3.schemeGreens,
  Greys: d3.schemeGreys,
  Oranges: d3.schemeOranges,
  Purples: d3.schemePurples,
  Reds: d3.schemeReds,
  BuGn: d3.schemeBuGn,
  BuPu: d3.schemeBuPu,
  GnBu: d3.schemeGnBu,
  OrRd: d3.schemeOrRd,
  PuBuGn: d3.schemePuBuGn,
  PuBu: d3.schemePuBu,
  PuRd: d3.schemePuRd,
} as const

export type SequentialSchemeName = keyof typeof SEQUENTIAL_SCHEMES

/**
 * Get a color from a sequential scheme based on a score (0-10).
 * Maps score to appropriate color intensity from the scheme.
 *
 * @param schemeName - Name of the sequential scheme to use
 * @param score - Score value (0-10)
 * @returns Hex color string
 */
export function getColorForScore(schemeName: SequentialSchemeName, score: number): string {
  if (score < 0 || score > 10) {
    throw new Error(`Score must be between 0 and 10, got ${score}`)
  }

  const scheme = SEQUENTIAL_SCHEMES[schemeName]

  // D3 sequential schemes have 9 levels (indices 0-8)
  // Map score 0-10 to index 0-8
  // Score 0 -> index 0 (lightest)
  // Score 10 -> index 8 (darkest)
  const maxIndex = 8
  const index = Math.min(Math.round((score / 10) * maxIndex), maxIndex)

  // Get the scheme array with 9 colors
  const colorArray = scheme[9]

  if (!colorArray) {
    throw new Error(`Sequential scheme ${schemeName} does not have a 9-color array`)
  }

  return colorArray[index]
}

/**
 * Agent color range configuration for interpolateOrRd.
 * We use a range of [0.4, 0.85] to:
 * - Avoid very light colors (< 0.4) that are hard to see
 * - Avoid very dark colors (> 0.85) that blend into backgrounds
 */
const AGENT_COLOR_RANGE = { min: 0.4, max: 0.85 }

/**
 * Get agent color from interpolateOrRd based on index and total count.
 * Evenly distributes agents across the OrRd gradient.
 *
 * @param index - Agent's index (0-based)
 * @param totalAgents - Total number of non-special agents
 * @returns RGB color string from interpolateOrRd
 */
function getAgentColorFromOrRd(index: number, totalAgents: number): string {
  const { min, max } = AGENT_COLOR_RANGE
  const range = max - min

  // Evenly distribute across the range
  const t = totalAgents <= 1
    ? (min + max) / 2  // Center if only one agent
    : min + (index / (totalAgents - 1)) * range

  return interpolateOrRd(t)
}

/**
 * Special colors for system agents and user-type agents.
 * These agents get fixed colors instead of colors from the sequential scheme.
 */
const SPECIAL_AGENT_COLORS: Record<string, string> = {
  'System': '#9ca3af',   // gray for system
  'User': '#64748b',     // slate gray for all user-type agents
}

/**
 * Normalize agent names for color consistency.
 * All user-type agents (You, User, UserProxy, user_proxy) get normalized to "User"
 * so they all receive the same color.
 */
function normalizeAgentNameForColor(name: string): string {
  const lower = name.toLowerCase()
  if (lower === 'you' || lower === 'user' || lower.includes('user_proxy') || lower.includes('userproxy')) {
    return 'User'
  }
  return name
}

/**
 * Agent color registry for sequential color assignment using interpolateOrRd.
 * Maps agent names to their assigned color indices and evenly distributes
 * colors across the OrRd gradient based on total agent count.
 *
 * Key features:
 * 1. Each agent gets a distinct color from the OrRd gradient
 * 2. Colors are evenly spread across the gradient range
 * 3. The same agent always gets the same color across the application
 * 4. Special agents (User, System) get fixed colors
 */
class AgentColorRegistry {
  private agentToColorIndex: Map<string, number> = new Map()
  private nextColorIndex: number = 0
  private registeredAgentCount: number = 0

  /**
   * Get or assign a color index for an agent.
   * If the agent hasn't been seen before, assigns the next available color index.
   * If the agent has been seen, returns their previously assigned index.
   */
  private getColorIndex(agentName: string): number {
    // Check if agent already has an assigned color
    const existingIndex = this.agentToColorIndex.get(agentName)
    if (existingIndex !== undefined) {
      return existingIndex
    }

    // Assign next color index and increment
    const newIndex = this.nextColorIndex
    this.agentToColorIndex.set(agentName, newIndex)
    this.nextColorIndex++
    this.registeredAgentCount++

    return newIndex
  }

  /**
   * Get total count of registered (non-special) agents.
   * Used for even distribution of colors across the gradient.
   */
  getTotalAgentCount(): number {
    return this.registeredAgentCount
  }

  /**
   * Get color for an agent using interpolateOrRd.
   * Special agents (User, System) get their designated colors.
   * User-type agents are normalized so they all get the same color.
   * Other agents get colors evenly distributed across the OrRd gradient.
   */
  getColor(agentName: string): string {
    // Normalize agent name first (e.g., "You", "UserProxy" -> "User")
    const normalized = normalizeAgentNameForColor(agentName)

    // Check for special agents first
    if (SPECIAL_AGENT_COLORS[normalized]) {
      return SPECIAL_AGENT_COLORS[normalized]
    }

    // Get sequential color index
    const colorIndex = this.getColorIndex(normalized)

    // Use at least the current count for even distribution
    // This ensures colors are spread even as new agents are added
    const totalAgents = Math.max(this.registeredAgentCount, 1)

    return getAgentColorFromOrRd(colorIndex, totalAgents)
  }

  /**
   * Reset the registry (useful for testing or new sessions).
   */
  reset(): void {
    this.agentToColorIndex.clear()
    this.nextColorIndex = 0
    this.registeredAgentCount = 0
  }

  /**
   * Pre-register multiple agents in the given order to ensure consistent color assignment.
   * Colors are assigned based on position in the array (first = lightest, last = darkest).
   * This should be called with sorted swimlane names to match vertical ordering.
   *
   * IMPORTANT: This resets existing registrations to ensure the new order takes effect.
   */
  registerAgents(agentNames: string[]): void {
    // Reset to ensure we use the new order
    this.reset()

    // Register each agent in order (preserving the order for color progression)
    agentNames.forEach(name => {
      const normalized = normalizeAgentNameForColor(name)
      // Skip special agents (they have fixed colors)
      if (!SPECIAL_AGENT_COLORS[normalized]) {
        // Only register if not already registered (handles duplicates)
        if (!this.agentToColorIndex.has(normalized)) {
          this.agentToColorIndex.set(normalized, this.nextColorIndex)
          this.nextColorIndex++
          this.registeredAgentCount++
        }
      }
    })
  }

  /**
   * Check if an agent has been registered (has a real color assigned).
   * Returns true if the agent is in the registry or is a special agent.
   */
  hasColor(agentName: string): boolean {
    const normalized = normalizeAgentNameForColor(agentName)
    if (SPECIAL_AGENT_COLORS[normalized]) {
      return true
    }
    return this.agentToColorIndex.has(normalized)
  }
}

// Singleton instance for global color consistency
const agentColorRegistry = new AgentColorRegistry()

/**
 * Get agent color by name using D3's interpolateOrRd sequential scheme.
 * Colors are evenly distributed across the OrRd gradient (orange to red).
 * Special agents (User, System) get fixed colors for consistency.
 *
 * @param agentName - Name of the agent
 * @returns RGB color string
 */
export function getAgentColorD3(agentName: string): string {
  return agentColorRegistry.getColor(agentName)
}

/**
 * Pre-register agents to ensure consistent color assignment.
 * Colors are assigned based on position in the array (first = lightest, last = darkest).
 * Call this with sorted swimlane names to match vertical ordering in the visualization.
 *
 * @param agentNames - Array of agent names in desired color order (typically sorted alphabetically)
 */
export function registerAgentColors(agentNames: string[]): void {
  agentColorRegistry.registerAgents(agentNames)
}

/**
 * Check if an agent has a registered color.
 * Returns true if the agent has been seen before or is a special agent.
 * Use this to determine if a color badge should be shown.
 *
 * @param agentName - Name of the agent
 * @returns True if the agent has a registered color
 */
export function hasAgentColor(agentName: string): boolean {
  return agentColorRegistry.hasColor(agentName)
}

/**
 * Reset the agent color registry (useful for new sessions or testing).
 */
export function resetAgentColorRegistry(): void {
  agentColorRegistry.reset()
}

/**
 * Default sequential scheme assignments for common analysis components.
 * These can be overridden when components are initialized.
 */
export const DEFAULT_ANALYSIS_SCHEMES: Record<string, SequentialSchemeName> = {
  'Sentiment': 'Reds',
  'Complexity': 'Oranges',
  'Risk': 'PuRd',
  'Bias': 'Purples',
  'Fact': 'Blues',
  'Logic': 'Greens',
  'Quality': 'BuGn',
  'Clarity': 'GnBu',
  'Relevance': 'BuPu',
  'Accuracy': 'PuBu',
  'Coherence': 'PuBuGn',
  'Consistency': 'OrRd',
}

/**
 * Assign a sequential scheme to an analysis component.
 * Uses default mapping if available, otherwise cycles through available schemes.
 *
 * @param componentLabel - Label of the analysis component
 * @param index - Index of the component (used for fallback cycling)
 * @returns Name of the sequential scheme to use
 */
export function assignSequentialScheme(componentLabel: string, index: number): SequentialSchemeName {
  // Try default mapping first
  if (DEFAULT_ANALYSIS_SCHEMES[componentLabel]) {
    return DEFAULT_ANALYSIS_SCHEMES[componentLabel]
  }

  // Fallback: cycle through available schemes
  const schemeNames = Object.keys(SEQUENTIAL_SCHEMES) as SequentialSchemeName[]
  return schemeNames[index % schemeNames.length]
}
