/**
 * TreeVisualization component displays the conversation tree with D3.js.
 *
 * Features:
 * - GitHub-style branch visualization
 * - Interactive zoom and pan
 * - Node highlighting for active branches
 * - Automatic centering on last user message
 * - Diminished opacity for inactive branches
 * - Keyboard shortcuts for navigation
 * - Responsive to tree updates
 */

import React, { useEffect, useRef, useState } from 'react'
import { TreeControls, useTreeKeyboardShortcuts } from './TreeControls'
import { useD3Tree } from './useD3Tree'
import { countNodes, getTreeDepth } from './treeUtils'
import { useToolCallsByNodeId, useToolExecutionsByNodeId } from '../../hooks/useResearchStore'
import type { TreeNode } from '../../types'

/**
 * Props for TreeVisualization component.
 */
interface TreeVisualizationProps {
  treeData: TreeNode | null
  currentBranchId: string
  className?: string
}

/**
 * TreeVisualization component renders the conversation tree.
 */
export function TreeVisualization({
  treeData,
  currentBranchId,
  className = '',
}: TreeVisualizationProps): React.ReactElement {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
  const toolCallsByNodeId = useToolCallsByNodeId()
  const toolExecutionsByNodeId = useToolExecutionsByNodeId()

  // Update dimensions on resize
  useEffect(() => {
    if (!containerRef.current) return

    const updateDimensions = (): void => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect()
        setDimensions({ width, height })
      }
    }

    updateDimensions()

    const resizeObserver = new ResizeObserver(updateDimensions)
    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
    }
  }, [])

  // Initialize D3 tree
  const { svgRef, root, recenter, zoomIn, zoomOut, resetZoom } = useD3Tree(
    treeData,
    currentBranchId,
    {
      width: dimensions.width,
      height: dimensions.height,
      maxVisibleHeight: 10,
      toolCallsByNodeId,
      toolExecutionsByNodeId,
    }
  )

  // Setup keyboard shortcuts
  useTreeKeyboardShortcuts({
    onRecenter: recenter,
    onZoomIn: zoomIn,
    onZoomOut: zoomOut,
    onResetZoom: resetZoom,
  })

  // Calculate tree stats
  const nodeCount = root ? countNodes(root) : 0
  const treeDepth = root ? getTreeDepth(root) : 0

  return (
    <div ref={containerRef} className={`relative w-full h-full ${className}`}>
      {/* Controls */}
      <TreeControls
        onRecenter={recenter}
        onZoomIn={zoomIn}
        onZoomOut={zoomOut}
        onResetZoom={resetZoom}
        nodeCount={nodeCount}
        treeDepth={treeDepth}
      />

      {/* Tree SVG */}
      {treeData ? (
        <svg
          ref={svgRef}
          width={dimensions.width}
          height={dimensions.height}
          className="w-full h-full bg-dark-bg"
          style={{ cursor: 'grab' }}
          onMouseDown={(e) => {
            if (e.currentTarget) {
              e.currentTarget.style.cursor = 'grabbing'
            }
          }}
          onMouseUp={(e) => {
            if (e.currentTarget) {
              e.currentTarget.style.cursor = 'grab'
            }
          }}
        />
      ) : (
        <EmptyTreeState />
      )}
    </div>
  )
}

/**
 * Empty state shown when there is no tree data.
 */
function EmptyTreeState(): React.ReactElement {
  return (
    <div className="flex items-center justify-center h-full bg-dark-bg">
      <div className="text-center">
        <div className="mb-4">
          <svg
            width="64"
            height="64"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="mx-auto text-gray-600"
          >
            <path
              d="M12 2L2 7L12 12L22 7L12 2Z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M2 17L12 22L22 17"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M2 12L12 17L22 12"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-500 mb-2">
          Waiting for the conversation to start...
        </h3>
      </div>
    </div>
  )
}

/**
 * Loading state shown while tree is being prepared.
 */
export function TreeVisualizationLoading(): React.ReactElement {
  return (
    <div className="flex items-center justify-center h-full bg-dark-bg">
      <div className="text-center">
        <div className="mb-4">
          <div className="w-12 h-12 border-4 border-dark-border border-t-dark-accent rounded-full animate-spin mx-auto" />
        </div>
        <p className="text-sm text-gray-500">Loading conversation tree...</p>
      </div>
    </div>
  )
}

/**
 * Error state shown when tree visualization fails.
 */
interface TreeVisualizationErrorProps {
  error: Error
  onRetry?: () => void
}

export function TreeVisualizationError({
  error,
  onRetry,
}: TreeVisualizationErrorProps): React.ReactElement {
  return (
    <div className="flex items-center justify-center h-full bg-dark-bg">
      <div className="text-center max-w-md p-6">
        <div className="mb-4">
          <svg
            width="64"
            height="64"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="mx-auto text-red-500"
          >
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
            <path d="M12 8V12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            <path d="M12 16H12.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-300 mb-2">
          Failed to Load Tree Visualization
        </h3>
        <p className="text-sm text-gray-500 mb-4">{error.message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-dark-accent text-white rounded hover:bg-opacity-80 transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  )
}
