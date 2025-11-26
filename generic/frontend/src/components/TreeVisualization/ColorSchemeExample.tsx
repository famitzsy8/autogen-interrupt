/**
 * Example demonstrating the D3 color scheme implementation.
 * This file shows how different scores map to different colors.
 */

import React from 'react'
import { getColorForScore, SEQUENTIAL_SCHEMES, type SequentialSchemeName } from '../../utils/colorSchemes'

/**
 * Example showing how scores map to colors for a single scheme
 */
export function ColorSchemeGradientExample(): React.ReactElement {
  const schemeName: SequentialSchemeName = 'Reds'
  const scores = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

  return (
    <div className="p-8 bg-dark-bg">
      <h2 className="text-xl font-bold text-dark-text mb-4">
        Color Scheme Example: {schemeName}
      </h2>
      <p className="text-sm text-gray-400 mb-6">
        Demonstrates how scores (0-10) map to color intensities
      </p>

      <div className="space-y-2">
        {scores.map((score) => {
          const color = getColorForScore(schemeName, score)
          return (
            <div key={score} className="flex items-center gap-4">
              <div className="w-24 text-sm text-gray-300">
                Score: {score}/10
              </div>
              <div
                className="flex-1 h-8 rounded-lg"
                style={{ backgroundColor: color }}
              />
              <div className="w-24 text-xs text-gray-500 font-mono">
                {color}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/**
 * Example showing all available sequential schemes
 */
export function AllSchemesExample(): React.ReactElement {
  const schemeNames = Object.keys(SEQUENTIAL_SCHEMES) as SequentialSchemeName[]
  const sampleScore = 7 // Show a consistent score across all schemes

  return (
    <div className="p-8 bg-dark-bg">
      <h2 className="text-xl font-bold text-dark-text mb-4">
        All Sequential Color Schemes
      </h2>
      <p className="text-sm text-gray-400 mb-6">
        Each analysis component can use any of these schemes (shown at score {sampleScore}/10)
      </p>

      <div className="grid grid-cols-2 gap-4">
        {schemeNames.map((schemeName) => {
          const color = getColorForScore(schemeName, sampleScore)
          return (
            <div key={schemeName} className="flex items-center gap-4">
              <div className="w-32 text-sm text-gray-300">
                {schemeName}
              </div>
              <div
                className="flex-1 h-12 rounded-lg"
                style={{ backgroundColor: color }}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}

/**
 * Example showing how multiple analysis components with different scores
 * would appear in the UI
 */
export function MultiComponentExample(): React.ReactElement {
  const components = [
    { label: 'Sentiment', scheme: 'Reds' as SequentialSchemeName, score: 8 },
    { label: 'Complexity', scheme: 'Oranges' as SequentialSchemeName, score: 6 },
    { label: 'Risk', scheme: 'PuRd' as SequentialSchemeName, score: 9 },
    { label: 'Bias', scheme: 'Purples' as SequentialSchemeName, score: 3 },
    { label: 'Fact', scheme: 'Blues' as SequentialSchemeName, score: 5 },
  ]

  return (
    <div className="p-8 bg-dark-bg">
      <h2 className="text-xl font-bold text-dark-text mb-4">
        Multi-Component Analysis Display
      </h2>
      <p className="text-sm text-gray-400 mb-6">
        Example of how different components with different scores appear together
      </p>

      <div className="space-y-4">
        {components.map((component) => {
          const color = getColorForScore(component.scheme, component.score)
          const barWidth = (component.score / 10) * 100

          return (
            <div key={component.label} className="space-y-2">
              <div className="flex items-center justify-between">
                <span
                  className="px-3 py-1 rounded-full text-xs font-medium text-white"
                  style={{ backgroundColor: color }}
                >
                  {component.label}
                </span>
                <span
                  className="text-lg font-bold"
                  style={{ color }}
                >
                  {component.score}/10
                </span>
              </div>

              {/* Progress bar with visual marker */}
              <div className="flex items-center gap-2">
                {/* Visual marker dot using darkest color from scheme */}
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{
                    backgroundColor: getColorForScore(component.scheme, 10), // Score 10 = index 8 (darkest)
                  }}
                  title={`${component.label} color scheme indicator`}
                />
                <div className="flex-1 h-6 bg-dark-border rounded-full overflow-hidden">
                  <div
                    className="h-full transition-all duration-300 rounded-full"
                    style={{
                      width: `${barWidth}%`,
                      backgroundColor: color,
                    }}
                  />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="mt-8 p-4 bg-dark-hover rounded-lg border border-dark-border">
        <h3 className="text-sm font-semibold text-dark-accent mb-2">
          Key Insights:
        </h3>
        <ul className="text-sm text-gray-400 space-y-1 list-disc list-inside">
          <li>Higher scores produce darker, more saturated colors</li>
          <li>Each component has a unique color scheme for easy identification</li>
          <li>Color intensity immediately conveys score magnitude</li>
          <li>Same component + same score = same color everywhere in the UI</li>
        </ul>
      </div>
    </div>
  )
}

/**
 * Complete demo showing all examples
 */
export function ColorSchemeDemo(): React.ReactElement {
  return (
    <div className="space-y-8">
      <ColorSchemeGradientExample />
      <AllSchemesExample />
      <MultiComponentExample />
    </div>
  )
}
