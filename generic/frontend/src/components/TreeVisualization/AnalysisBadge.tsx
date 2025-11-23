/**
 * AnalysisBadge component for displaying analysis component badges on tree nodes.
 *
 * Features:
 * - Displays analysis components as colored badges based on their scores
 * - Uses D3 sequential color schemes for score-based coloring
 * - Shows tooltips with component descriptions on hover
 * - Supports click interactions for each component
 * - Responsive and non-cluttered design
 */

import React from 'react'
import type { AnalysisComponent, ComponentScore } from '../../types'
import { getColorForScore, assignSequentialScheme, type SequentialSchemeName } from '../../utils/colorSchemes'

/**
 * Props for AnalysisBadge component.
 */
interface AnalysisBadgeProps {
  /** List of analysis components to display */
  components: AnalysisComponent[]
  /** Scores for each component (optional - if not provided, uses mid-range colors) */
  scores?: Record<string, ComponentScore>
  /** Show labels (true) or circles (false). Default: false */
  isExpanded?: boolean
  /** Click handler for individual components */
  onClick?: (component: AnalysisComponent) => void
}

/**
 * AnalysisBadge component displays analysis components as visual indicators.
 * Returns null if no components are provided.
 */
export function AnalysisBadge({
  components,
  scores,
  isExpanded = false,
  onClick,
}: AnalysisBadgeProps): React.ReactElement | null {
  // Return null if no components to display
  if (components.length === 0) {
    return null
  }

  const handleClick = (
    component: AnalysisComponent,
    event: React.MouseEvent
  ): void => {
    event.stopPropagation()
    if (onClick) {
      onClick(component)
    }
  }

  return (
    <div className="flex flex-wrap gap-1">
      {isExpanded ? (
        // Expanded mode: Show labeled badges with score-based colors
        components.map((component, index) => {
          const schemeName = (component.sequentialScheme as SequentialSchemeName) || assignSequentialScheme(component.label, index)
          const score = scores?.[component.label]?.score ?? 5 // Default to mid-range if no score
          const badgeColor = getColorForScore(schemeName, score)

          return (
            <button
              key={component.label}
              className="px-2 py-0.5 rounded-xl text-[11px] text-white font-medium cursor-pointer transition-opacity hover:opacity-80"
              style={{ backgroundColor: badgeColor }}
              onClick={(event) => handleClick(component, event)}
              title={`${component.label}: ${component.description}${score ? ` (${score}/10)` : ''}`}
              aria-label={`${component.label}: ${component.description}`}
            >
              {component.label}
            </button>
          )
        })
      ) : (
        // Collapsed mode: Show colored circles with score-based colors
        components.map((component, index) => {
          const schemeName = (component.sequentialScheme as SequentialSchemeName) || assignSequentialScheme(component.label, index)
          const score = scores?.[component.label]?.score ?? 5 // Default to mid-range if no score
          const badgeColor = getColorForScore(schemeName, score)

          return (
            <button
              key={component.label}
              className="w-3 h-3 rounded-full cursor-pointer transition-transform hover:scale-125"
              style={{ backgroundColor: badgeColor }}
              onClick={(event) => handleClick(component, event)}
              title={`${component.label}${score ? `: ${score}/10` : ''}`}
              aria-label={component.label}
            />
          )
        })
      )}
    </div>
  )
}
