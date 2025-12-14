/**
 * AnalysisScoreDisplay shows detailed analysis scores for a node.
 *
 * Features:
 * - Displays all component scores with visual indicators
 * - Color-coded score values using D3 sequential schemes based on score intensity
 * - Visual progress bar showing score magnitude
 * - Conditional reasoning display (only shown when score >= threshold)
 * - Highlighted display for triggered components
 * - Empty state when no scores available
 */

import React from 'react'
import type { AnalysisComponent, ComponentScore } from '../../types'
import { getColorForScore, assignSequentialScheme, type SequentialSchemeName } from '../../utils/colorSchemes'

interface AnalysisScoreDisplayProps {
  components: AnalysisComponent[]
  scores: Record<string, ComponentScore>
  triggerThreshold?: number
}

export function AnalysisScoreDisplay({
  components,
  scores,
  triggerThreshold = 8,
}: AnalysisScoreDisplayProps): React.ReactElement {
  // Show empty state if no scores available
  if (Object.keys(scores).length === 0) {
    return (
      <div className="p-4 text-center text-dark-text-muted italic text-sm">
        No analysis scores available
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-dark-accent mb-3">Analysis Scores</h3>

      {components.map((component, index) => {
        const score = scores[component.label]

        // Skip if no score for this component
        if (!score) {
          return null
        }

        const isTriggered = score.score >= triggerThreshold
        const scorePercentage = score.score * 10

        // Determine sequential scheme for this component
        const schemeName = (component.sequentialScheme as SequentialSchemeName) || assignSequentialScheme(component.label, index)

        // Get color based on the actual score value
        const scoreColor = getColorForScore(schemeName, score.score)
        const badgeColor = getColorForScore(schemeName, 5) // Mid-range color for badge

        return (
          <div
            key={component.label}
            className={`rounded-lg border overflow-hidden transition-colors ${
              isTriggered
                ? 'bg-red-50 border-red-400'
                : 'bg-dark-hover border-dark-border'
            }`}
          >
            {/* Score Header */}
            <div className="p-3">
              <div className="flex items-center justify-between mb-2">
                {/* Component Badge - uses mid-range color from scheme */}
                <span
                  className="px-3 py-1 rounded-full text-xs font-medium text-white"
                  style={{ backgroundColor: badgeColor }}
                >
                  {component.label}
                </span>

                {/* Score Value - uses score-based color */}
                <span
                  className="text-lg font-bold"
                  style={{ color: scoreColor }}
                >
                  {score.score}/10
                </span>
              </div>

              {/* Component Description */}
              <p className="text-xs text-dark-text-secondary mb-2">{component.description}</p>

              {/* Reasoning - Only shown if score >= threshold */}
              {score.reasoning && isTriggered && (
                <div className="mt-3 p-2 bg-amber-50 border-l-2 border-amber-500 rounded">
                  <p className="text-xs text-dark-text">
                    <span className="font-semibold text-amber-700">Reasoning:</span>{' '}
                    {score.reasoning}
                  </p>
                </div>
              )}

              {/* Visual Score Bar - uses score-based color */}
              <div className="mt-3 flex items-center gap-2">
                {/* Visual marker dot using darkest color from scheme */}
                <div
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{
                    backgroundColor: getColorForScore(schemeName, 10), // Score 10 = index 8 (darkest)
                  }}
                  title={`${component.label} color scheme indicator`}
                />
                <div className="flex-1 h-4.5 rounded-full overflow-hidden border border-dark-border" style={{ backgroundColor: 'var(--color-surface)' }}>
                  <div
                    className="h-full transition-all duration-300 ease-out rounded-full"
                    style={{
                      width: `${scorePercentage}%`,
                      backgroundColor: scoreColor,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
