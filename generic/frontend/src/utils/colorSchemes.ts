/**
 * Color scheme utilities using D3.js d3-scale-chromatic
 *
 * This module provides:
 * 1. Agent colors using schemeDark2 categorical scheme
 * 2. Analysis component colors using sequential schemes
 * 3. Score-based color selection for visualizations
 */

import { schemeDark2 } from 'd3-scale-chromatic'
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
 * Agent color palette using D3's Dark2 categorical scheme.
 * Dark2 provides 8 distinct colors suitable for categorical data.
 */
export const AGENT_COLORS_D3 = schemeDark2

/**
 * Special colors for system agents (not from D3 schemes).
 */
const SPECIAL_AGENT_COLORS: Record<string, string> = {
  'You': '#ffffff',      // white for user
  'User': '#ffffff',     // white for user
  'System': '#9ca3af',   // gray for system
}

/**
 * Agent color registry for sequential color assignment.
 * Maps agent names to their assigned color indices to ensure:
 * 1. Each agent gets a distinct color
 * 2. Colors are assigned sequentially in order of first encounter
 * 3. The same agent always gets the same color across the application
 */
class AgentColorRegistry {
  private agentToColorIndex: Map<string, number> = new Map()
  private nextColorIndex: number = 0

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
    this.nextColorIndex = (this.nextColorIndex + 1) % AGENT_COLORS_D3.length

    return newIndex
  }

  /**
   * Get color for an agent. Assigns sequentially on first encounter.
   * Special agents (User, System) get their designated colors.
   */
  getColor(agentName: string): string {
    // Check for special agents first
    if (SPECIAL_AGENT_COLORS[agentName]) {
      return SPECIAL_AGENT_COLORS[agentName]
    }

    // Get sequential color index
    const colorIndex = this.getColorIndex(agentName)
    return AGENT_COLORS_D3[colorIndex]
  }

  /**
   * Reset the registry (useful for testing or new sessions).
   */
  reset(): void {
    this.agentToColorIndex.clear()
    this.nextColorIndex = 0
  }

  /**
   * Pre-register multiple agents in order to ensure consistent color assignment.
   * This should be called when agent names are first known (e.g., from tree traversal).
   */
  registerAgents(agentNames: string[]): void {
    agentNames.forEach(name => {
      // Skip special agents
      if (!SPECIAL_AGENT_COLORS[name]) {
        this.getColorIndex(name)
      }
    })
  }
}

// Singleton instance for global color consistency
const agentColorRegistry = new AgentColorRegistry()

/**
 * Get agent color by name using D3's Dark2 scheme.
 * Uses special colors for system agents, otherwise assigns colors sequentially
 * in the order agents are first encountered.
 *
 * @param agentName - Name of the agent
 * @returns Hex color string
 */
export function getAgentColorD3(agentName: string): string {
  return agentColorRegistry.getColor(agentName)
}

/**
 * Pre-register agents to ensure consistent color assignment.
 * Call this when you first know all agent names (e.g., from tree extraction).
 *
 * @param agentNames - Array of agent names in order of first appearance
 */
export function registerAgentColors(agentNames: string[]): void {
  agentColorRegistry.registerAgents(agentNames)
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
