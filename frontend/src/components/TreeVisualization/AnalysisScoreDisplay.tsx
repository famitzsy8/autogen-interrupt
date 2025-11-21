/**
 * AnalysisScoreDisplay shows detailed analysis scores for a node.
 *
 * Features:
 * - Displays all component scores with visual indicators
 * - Color-coded score values (red for high scores >= 8, green for low scores)
 * - Visual progress bar showing score magnitude
 * - Conditional reasoning display (only shown when score >= threshold)
 * - Highlighted display for triggered components
 * - Empty state when no scores available
 */

import React from 'react'
import type { AnalysisComponent, ComponentScore } from '../../types'

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
      <div className="p-4 text-center text-gray-500 italic text-sm">
        No analysis scores available
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-dark-accent mb-3">Analysis Scores</h3>

      {components.map((component) => {
        const score = scores[component.label]

        // Skip if no score for this component
        if (!score) {
          return null
        }

        const isTriggered = score.score >= triggerThreshold
        const scorePercentage = score.score * 10

        // Determine score color (red for high, green for low)
        const scoreColorClass = isTriggered ? 'text-red-400' : 'text-green-400'
        const barColor = isTriggered ? '#ef4444' : '#10b981'

        return (
          <div
            key={component.label}
            className={`rounded-lg border overflow-hidden transition-colors ${
              isTriggered
                ? 'bg-red-900/10 border-red-800'
                : 'bg-dark-hover border-dark-border'
            }`}
          >
            {/* Score Header */}
            <div className="p-3">
              <div className="flex items-center justify-between mb-2">
                {/* Component Badge */}
                <span
                  className="px-3 py-1 rounded-full text-xs font-medium text-white"
                  style={{ backgroundColor: component.color }}
                >
                  {component.label}
                </span>

                {/* Score Value */}
                <span className={`text-lg font-bold ${scoreColorClass}`}>
                  {score.score}/10
                </span>
              </div>

              {/* Component Description */}
              <p className="text-xs text-gray-400 mb-2">{component.description}</p>

              {/* Reasoning - Only shown if score >= threshold */}
              {score.reasoning && isTriggered && (
                <div className="mt-3 p-2 bg-yellow-900/20 border-l-2 border-yellow-600 rounded">
                  <p className="text-xs text-gray-300">
                    <span className="font-semibold text-yellow-500">Reasoning:</span>{' '}
                    {score.reasoning}
                  </p>
                </div>
              )}

              {/* Visual Score Bar */}
              <div className="mt-3 h-1.5 bg-dark-border rounded-full overflow-hidden">
                <div
                  className="h-full transition-all duration-300 ease-out"
                  style={{
                    width: `${scorePercentage}%`,
                    backgroundColor: barColor,
                  }}
                />
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
