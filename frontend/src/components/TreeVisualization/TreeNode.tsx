/**
 * TreeNode component for rendering individual nodes in the conversation tree.
 *
 * This component is currently not used as nodes are rendered directly in D3,
 * but it's provided for future extensibility if we need React-based node rendering.
 *
 * Features:
 * - Displays agent name and message preview
 * - Shows visual indicators for node state
 * - Handles click interactions
 * - Supports tooltips on hover
 */

import React from 'react'
import type { TreeNode as TreeNodeType } from '../../types'
import { getAgentColorD3 } from '../../utils/colorSchemes'

/**
 * Props for TreeNode component.
 */
interface TreeNodeProps {
  node: TreeNodeType
  isActive: boolean
  isInActivePath: boolean
  onClick?: (nodeId: string) => void
  position: { x: number; y: number }
}

/**
 * TreeNode component for React-based rendering (currently unused).
 * Nodes are rendered directly in D3 for better performance and animations.
 */
export function TreeNode({
  node,
  isInActivePath,
  onClick,
  position,
}: TreeNodeProps): React.ReactElement {
  const agentColor = getAgentColorD3(node.agent_name)
  const displayName = node.display_name

  const opacity = node.is_active ? (isInActivePath ? 1 : 0.6) : 0.3

  const handleClick = (): void => {
    if (onClick) {
      onClick(node.id)
    }
  }

  return (
    <g
      transform={`translate(${position.y}, ${position.x})`}
      style={{ opacity }}
      onClick={handleClick}
      className="cursor-pointer"
    >
      {/* Node circle */}
      <circle
        r={8}
        fill={agentColor}
        stroke={isInActivePath ? '#58a6ff' : '#c9d1d9'}
        strokeWidth={isInActivePath ? 3 : 2}
        className="transition-all duration-300"
      />

      {/* Node label */}
      <text
        dy="0.31em"
        x={node.children.length > 0 ? -12 : 12}
        textAnchor={node.children.length > 0 ? 'end' : 'start'}
        fill="#c9d1d9"
        fontSize={12}
        fontFamily="sans-serif"
      >
        {displayName}
      </text>

      {/* Background stroke for text readability */}
      <text
        dy="0.31em"
        x={node.children.length > 0 ? -12 : 12}
        textAnchor={node.children.length > 0 ? 'end' : 'start'}
        fill="none"
        stroke="#0d1117"
        strokeWidth={3}
        fontSize={12}
        fontFamily="sans-serif"
      >
        {displayName}
      </text>

      {/* Tooltip */}
      <title>
        {displayName}: {node.message.substring(0, 100)}
        {node.message.length > 100 ? '...' : ''}
      </title>
    </g>
  )
}

/**
 * Props for TreeNodeInfo component.
 */
interface TreeNodeInfoProps {
  node: TreeNodeType | null
  onClose: () => void
}

/**
 * TreeNodeInfo component displays detailed information about a selected node.
 */
export function TreeNodeInfo({ node, onClose }: TreeNodeInfoProps): React.ReactElement | null {
  if (!node) return null

  const agentColor = getAgentColorD3(node.agent_name)
  const displayName = node.display_name

  return (
    <div className="absolute top-4 right-4 bg-dark-hover border border-dark-border rounded-lg p-4 max-w-md shadow-lg z-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className="px-3 py-1 rounded text-sm font-semibold"
            style={{ backgroundColor: agentColor, color: '#ffffff' }}
          >
            {displayName}
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-dark-text-muted hover:text-dark-text transition-colors"
          aria-label="Close"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M12 4L4 12M4 4L12 12"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </div>

      {/* Message content */}
      <div className="mb-3">
        <p className="text-xs text-dark-text-secondary mb-1">Message:</p>
        <p className="text-sm text-dark-text leading-relaxed">{node.message}</p>
      </div>

      {/* Metadata */}
      <div className="space-y-1 text-xs text-dark-text-muted">
        <div className="flex items-center gap-2">
          <span>Branch ID:</span>
          <span className="text-dark-text-secondary">{node.branch_id}</span>
        </div>
        <div className="flex items-center gap-2">
          <span>Status:</span>
          <span
            className={`px-2 py-0.5 rounded ${
              node.is_active
                ? 'bg-green-900 text-green-300'
                : 'bg-dark-surface text-dark-text-secondary'
            }`}
          >
            {node.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span>Children:</span>
          <span className="text-dark-text-secondary">{node.children.length}</span>
        </div>
        <div className="flex items-center gap-2">
          <span>Timestamp:</span>
          <span className="text-dark-text-secondary">
            {new Date(node.timestamp).toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  )
}
