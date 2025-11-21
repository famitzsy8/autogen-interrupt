/**
 * Example usage of AnalysisScoreDisplay component
 *
 * This file demonstrates how to use the AnalysisScoreDisplay component
 * with sample data.
 */

import React from 'react'
import { AnalysisScoreDisplay } from './AnalysisScoreDisplay'
import type { AnalysisComponent, ComponentScore } from '../../types'

// Example analysis components configuration
const exampleComponents: AnalysisComponent[] = [
  {
    label: 'Sentiment',
    description: 'Tracks negative or concerning sentiment in the conversation',
    color: '#ef4444',
  },
  {
    label: 'Complexity',
    description: 'Measures the complexity of the current task or discussion',
    color: '#f59e0b',
  },
  {
    label: 'Risk',
    description: 'Identifies potential risks or problematic patterns',
    color: '#dc2626',
  },
]

// Example scores - high score triggers (>= 8)
const exampleScoresTriggered: Record<string, ComponentScore> = {
  'Sentiment': {
    score: 9,
    reasoning: 'Multiple instances of frustration and concern detected in recent messages',
  },
  'Complexity': {
    score: 7,
    reasoning: '', // No reasoning for scores < threshold
  },
  'Risk': {
    score: 8,
    reasoning: 'Potential data loss scenario identified in the discussion',
  },
}

// Example scores - low scores (< 8)
const exampleScoresNormal: Record<string, ComponentScore> = {
  'Sentiment': {
    score: 3,
    reasoning: '',
  },
  'Complexity': {
    score: 5,
    reasoning: '',
  },
  'Risk': {
    score: 2,
    reasoning: '',
  },
}

// Example empty scores
const exampleScoresEmpty: Record<string, ComponentScore> = {}

export function AnalysisScoreDisplayExample(): React.ReactElement {
  return (
    <div className="p-8 space-y-8 bg-dark-bg min-h-screen">
      <div>
        <h2 className="text-xl font-bold text-dark-text mb-4">
          Example 1: Triggered Components (High Scores)
        </h2>
        <div className="bg-dark-hover p-4 rounded-lg border border-dark-border">
          <AnalysisScoreDisplay
            components={exampleComponents}
            scores={exampleScoresTriggered}
            triggerThreshold={8}
          />
        </div>
      </div>

      <div>
        <h2 className="text-xl font-bold text-dark-text mb-4">
          Example 2: Normal Scores (Below Threshold)
        </h2>
        <div className="bg-dark-hover p-4 rounded-lg border border-dark-border">
          <AnalysisScoreDisplay
            components={exampleComponents}
            scores={exampleScoresNormal}
            triggerThreshold={8}
          />
        </div>
      </div>

      <div>
        <h2 className="text-xl font-bold text-dark-text mb-4">
          Example 3: Empty State (No Scores)
        </h2>
        <div className="bg-dark-hover p-4 rounded-lg border border-dark-border">
          <AnalysisScoreDisplay
            components={exampleComponents}
            scores={exampleScoresEmpty}
            triggerThreshold={8}
          />
        </div>
      </div>
    </div>
  )
}
