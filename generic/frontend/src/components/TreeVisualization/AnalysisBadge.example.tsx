/**
 * Example usage of the AnalysisBadge component.
 * This file demonstrates how to use the component with different configurations.
 */

import React from 'react'
import { AnalysisBadge } from './AnalysisBadge'
import type { AnalysisComponent } from '../../types'

/**
 * Example analysis components that might be used in the tree visualization
 */
const exampleComponents: AnalysisComponent[] = [
  {
    label: 'Bias',
    description: 'Detecting potential bias in the conversation',
    color: '#ff6b6b',
  },
  {
    label: 'Fact',
    description: 'Fact-checking accuracy of statements',
    color: '#4ecdc4',
  },
  {
    label: 'Logic',
    description: 'Analyzing logical reasoning quality',
    color: '#45b7d1',
  },
]

/**
 * Example: Collapsed view (default)
 * Shows small colored circles, perfect for tree nodes with limited space
 */
export function CollapsedBadgeExample(): React.ReactElement {
  return (
    <div className="p-4 bg-dark-bg border border-dark-border rounded">
      <h3 className="text-sm text-gray-400 mb-2">Collapsed View:</h3>
      <AnalysisBadge components={exampleComponents} />
    </div>
  )
}

/**
 * Example: Expanded view
 * Shows full labels with background colors, better for detail views
 */
export function ExpandedBadgeExample(): React.ReactElement {
  return (
    <div className="p-4 bg-dark-bg border border-dark-border rounded">
      <h3 className="text-sm text-gray-400 mb-2">Expanded View:</h3>
      <AnalysisBadge components={exampleComponents} isExpanded={true} />
    </div>
  )
}

/**
 * Example: With click handler
 * Demonstrates interactive badges that respond to user clicks
 */
export function InteractiveBadgeExample(): React.ReactElement {
  const [clicked, setClicked] = React.useState<string | null>(null)

  const handleClick = (component: AnalysisComponent): void => {
    setClicked(component.label)
    setTimeout(() => setClicked(null), 2000)
  }

  return (
    <div className="p-4 bg-dark-bg border border-dark-border rounded">
      <h3 className="text-sm text-gray-400 mb-2">Interactive (click a badge):</h3>
      <AnalysisBadge
        components={exampleComponents}
        isExpanded={true}
        onClick={handleClick}
      />
      {clicked && (
        <p className="text-xs text-green-400 mt-2">Clicked: {clicked}</p>
      )}
    </div>
  )
}

/**
 * Example: Empty state
 * Component returns null when there are no components to display
 */
export function EmptyBadgeExample(): React.ReactElement {
  return (
    <div className="p-4 bg-dark-bg border border-dark-border rounded">
      <h3 className="text-sm text-gray-400 mb-2">Empty State (returns null):</h3>
      <AnalysisBadge components={[]} />
      <p className="text-xs text-gray-500 mt-2">
        No badges rendered when components array is empty
      </p>
    </div>
  )
}

/**
 * Example: Single component
 * Shows how the component handles a single analysis component
 */
export function SingleBadgeExample(): React.ReactElement {
  const singleComponent: AnalysisComponent[] = [
    {
      label: 'Quality',
      description: 'Overall response quality assessment',
      color: '#95e1d3',
    },
  ]

  return (
    <div className="p-4 bg-dark-bg border border-dark-border rounded">
      <h3 className="text-sm text-gray-400 mb-2">Single Component:</h3>
      <div className="flex gap-4 items-center">
        <div>
          <p className="text-xs text-gray-500 mb-1">Collapsed:</p>
          <AnalysisBadge components={singleComponent} />
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Expanded:</p>
          <AnalysisBadge components={singleComponent} isExpanded={true} />
        </div>
      </div>
    </div>
  )
}

/**
 * Complete demo component showing all examples
 */
export function AnalysisBadgeDemo(): React.ReactElement {
  return (
    <div className="space-y-4 p-8">
      <h2 className="text-xl text-dark-text font-bold mb-4">
        AnalysisBadge Component Examples
      </h2>
      <CollapsedBadgeExample />
      <ExpandedBadgeExample />
      <InteractiveBadgeExample />
      <SingleBadgeExample />
      <EmptyBadgeExample />
    </div>
  )
}
