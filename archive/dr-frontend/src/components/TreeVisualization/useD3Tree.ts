/**
 * Custom hook for managing D3 tree visualization state and operations.
 *
 * Handles:
 * - D3 tree layout calculations
 * - SVG element management
 * - Zoom and pan interactions
 * - Tree updates and animations
 * - Node visibility and collapsing
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import * as d3 from 'd3'
import type { TreeNode, ToolCall, ToolExecution, ToolExecutionResult } from '../../types'
import type { D3TreeNode, TreeConfig } from './treeUtils'
import {
  convertToD3Hierarchy,
  findActivePath,
  findVisibleNodes,
  collapseInvisibleNodes,
  findLastMessageNode,
  DEFAULT_TREE_CONFIG,
} from './treeUtils'

/**
 * Hook configuration options.
 */
interface UseD3TreeOptions {
  width: number
  height: number
  config?: Partial<TreeConfig>
  maxVisibleHeight?: number
  toolCallsByNodeId?: Record<string, ToolCall>
  toolExecutionsByNodeId?: Record<string, ToolExecution>
}

/**
 * Hook return value.
 */
interface UseD3TreeReturn {
  svgRef: React.RefObject<SVGSVGElement>
  root: D3TreeNode | null
  activeNodeIds: Set<string>
  centerNodeId: string | null
  recenter: () => void
  zoomIn: () => void
  zoomOut: () => void
  resetZoom: () => void
}

/**
 * Animation duration in milliseconds.
 */
const ANIMATION_DURATION = 300

/**
 * Apply pulsing animation to a badge while it's executing.
 */
function applyPulsingAnimation(
  badge: d3.Selection<SVGGElement, unknown, null, undefined>,
  isExecuting: boolean
): void {
  if (isExecuting) {
    // Start pulsing animation
    function pulse(this: SVGGElement) {
      d3.select(this)
        .transition()
        .duration(800)
        .style('opacity', 0.4)
        .transition()
        .duration(800)
        .style('opacity', 1)
        .on('end', function() {
          // Check if badge still exists and should continue pulsing
          const element = d3.select(this)
          if (element.node() && element.attr('data-pulsing') === 'true') {
            pulse.call(this)
          }
        })
    }

    badge.attr('data-pulsing', 'true')
    pulse.call(badge.node() as SVGGElement)
  } else {
    // Stop pulsing, ensure full opacity
    badge.attr('data-pulsing', 'false')
    badge.interrupt() // Stop any ongoing transitions
    badge.style('opacity', 1)
  }
}

/**
 * Get color for tool based on type.
 */
function getToolColor(toolName: string): { bg: string; border: string } {
  const name = toolName.toLowerCase()

  // Web/network tools
  if (name.includes('web') || name.includes('search') || name.includes('browse')) {
    return { bg: '#1f6feb', border: '#58a6ff' }
  }

  // File/code tools
  if (name.includes('file') || name.includes('read') || name.includes('write') || name.includes('code')) {
    return { bg: '#8b5cf6', border: '#a78bfa' }
  }

  // Math/calculation tools
  if (name.includes('calc') || name.includes('math') || name.includes('compute')) {
    return { bg: '#10b981', border: '#34d399' }
  }

  // Database/data tools
  if (name.includes('db') || name.includes('database') || name.includes('query')) {
    return { bg: '#f59e0b', border: '#fbbf24' }
  }

  // Default color
  return { bg: '#6b7280', border: '#9ca3af' }
}

/**
 * Custom hook for D3 tree visualization.
 * @param treeData - Root node of the conversation tree
 * @param currentBranchId - Current active branch ID
 * @param options - Configuration options
 * @returns Tree state and control functions
 */
export function useD3Tree(
  treeData: TreeNode | null,
  currentBranchId: string,
  options: UseD3TreeOptions
): UseD3TreeReturn {
  const { width, height, config = {}, maxVisibleHeight = 30, toolCallsByNodeId = {}, toolExecutionsByNodeId = {} } = options

  const svgRef = useRef<SVGSVGElement>(null)
  const gRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null)
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const transformRef = useRef<d3.ZoomTransform>(d3.zoomIdentity)

  const [root, setRoot] = useState<D3TreeNode | null>(null)
  const [activeNodeIds, setActiveNodeIds] = useState<Set<string>>(new Set())
  const [centerNodeId, setCenterNodeId] = useState<string | null>(null)

  const treeConfig: TreeConfig = { ...DEFAULT_TREE_CONFIG, ...config }

  /**
   * Initialize D3 tree and setup zoom behavior.
   */
  useEffect(() => {
    if (!svgRef.current || !treeData) return

    const svg = d3.select(svgRef.current)

    // Clear existing content
    svg.selectAll('*').remove()

    // Create main group for tree content
    const g = svg.append('g').attr('class', 'tree-container')
    gRef.current = g

    // Setup zoom behavior
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 3])
      .on('zoom', (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
        g.attr('transform', event.transform.toString())
        transformRef.current = event.transform
      })

    svg.call(zoom)
    zoomRef.current = zoom

    // Convert tree data to D3 hierarchy
    const hierarchy = convertToD3Hierarchy(treeData)

    // Initialize node positions
    hierarchy.x0 = width / 2
    hierarchy.y0 = 0

    // Store hierarchy in state
    setRoot(hierarchy)

    // Find active path
    const activePath = findActivePath(hierarchy, currentBranchId)
    setActiveNodeIds(activePath)

    // Find last user message node to center on
    const lastMessageNode = findLastMessageNode(hierarchy, currentBranchId)
    if (lastMessageNode) {
      setCenterNodeId(lastMessageNode.data.id)
      console.log('lastMessageNode', lastMessageNode)
      console.log('lastMessageNode.data.id', lastMessageNode.data.id)
      console.log('lastMessageNode.data.agent_name', lastMessageNode.data.agent_name)
      console.log('lastMessageNode.data.is_active', lastMessageNode.data.is_active)
      console.log('lastMessageNode.data.timestamp', lastMessageNode.data.timestamp)
      console.log('lastMessageNode.data.message', lastMessageNode.data.message)
      console.log('lastMessageNode.data.parent', lastMessageNode.data.parent)
      console.log('lastMessageNode.data.children', lastMessageNode.data.children)
    }
  }, [treeData, currentBranchId, width, height])

  /**
   * Update tree visualization when data or configuration changes.
   */
  useEffect(() => {
    if (!root || !gRef.current) return

    updateTree(root, gRef.current, {
      width,
      height,
      config: treeConfig,
      activeNodeIds,
      centerNodeId,
      maxVisibleHeight,
      toolCallsByNodeId,
      toolExecutionsByNodeId,
    })
  }, [root, activeNodeIds, centerNodeId, width, height, maxVisibleHeight, treeConfig, toolCallsByNodeId, toolExecutionsByNodeId])

  /**
   * Update center node when tree data changes to keep view on latest messages.
   */
  useEffect(() => {
    if (!root) return

    const lastMessageNode = findLastMessageNode(root, currentBranchId)
    if (lastMessageNode && lastMessageNode.data.id !== centerNodeId) {
      setCenterNodeId(lastMessageNode.data.id)
    }
  }, [root, centerNodeId, currentBranchId])

  /**
   * Recenter the view on the last user message or root.
   */
  const recenter = useCallback(() => {
    if (!root || !svgRef.current || !zoomRef.current) return

    const lastMessageNode = findLastMessageNode(root, currentBranchId)
    const targetNode = lastMessageNode || root

    if (targetNode) {
      // Calculate transform to center the node
      const svg = d3.select(svgRef.current)
      const scale = transformRef.current.k
      const x = -targetNode.x! * scale + width / 2
      const y = -targetNode.y! * scale + height / 3

      svg
        .transition()
        .duration(ANIMATION_DURATION)
        .call(zoomRef.current.transform, d3.zoomIdentity.translate(x, y).scale(scale))
    }
  }, [root, width, height, currentBranchId])

  /**
   * Automatically recenter the view when the centerNodeId changes.
   */
  useEffect(() => {
    if (centerNodeId) {
      recenter()
    }
  }, [centerNodeId, recenter])

  /**
   * Zoom in on the tree.
   */
  const zoomIn = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return

    const svg = d3.select(svgRef.current)
    svg.transition().duration(ANIMATION_DURATION).call(zoomRef.current.scaleBy, 1.3)
  }, [])

  /**
   * Zoom out on the tree.
   */
  const zoomOut = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return

    const svg = d3.select(svgRef.current)
    svg.transition().duration(ANIMATION_DURATION).call(zoomRef.current.scaleBy, 0.7)
  }, [])

  /**
   * Reset zoom to default view.
   */
  const resetZoom = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return

    const svg = d3.select(svgRef.current)
    svg
      .transition()
      .duration(ANIMATION_DURATION)
      .call(zoomRef.current.transform, d3.zoomIdentity.translate(50, height / 2))
  }, [height])

  return {
    svgRef,
    root,
    activeNodeIds,
    centerNodeId,
    recenter,
    zoomIn,
    zoomOut,
    resetZoom,
  }
}

/**
 * Update tree visualization with new data.
 */
interface UpdateTreeOptions {
  width: number
  height: number
  config: TreeConfig
  activeNodeIds: Set<string>
  centerNodeId: string | null
  maxVisibleHeight: number
  toolCallsByNodeId: Record<string, ToolCall>
  toolExecutionsByNodeId: Record<string, ToolExecution>
}

function updateTree(
  root: D3TreeNode,
  g: d3.Selection<SVGGElement, unknown, null, undefined>,
  options: UpdateTreeOptions
): void {
  const { width, height, config, activeNodeIds, centerNodeId, maxVisibleHeight, toolCallsByNodeId, toolExecutionsByNodeId } = options

  // Find visible nodes based on center and max height
  const visibleNodeIds = findVisibleNodes(root, centerNodeId, maxVisibleHeight)

  // Collapse nodes that shouldn't be visible
  collapseInvisibleNodes(root, visibleNodeIds)

  // Create tree layout
  const treeLayout = d3
    .tree<TreeNode>()
    .size([width - 200, height - 100])
    .separation((a, b) => (a.parent === b.parent ? 1 : 2))

  // Apply layout
  const treeData = treeLayout(root)
  const nodes = treeData.descendants() as D3TreeNode[]
  const links = treeData.links() as d3.HierarchyPointLink<TreeNode>[]

  // Normalize horizontal position based on depth
  nodes.forEach((node) => {
    node.y = node.depth * config.verticalSpacing
  })

  // Update links
  const link = g
    .selectAll<SVGPathElement, d3.HierarchyPointLink<TreeNode>>('.link')
    .data(links, (d) => (d.target as D3TreeNode).data.id)

  // Enter new links
  const linkEnter = link
    .enter()
    .insert('path', 'g')
    .attr('class', 'link')
    .attr('fill', 'none')
    .attr('stroke', '#30363d')
    .attr('stroke-width', 2)
    .attr('d', (d) => {
      const source = d.source as D3TreeNode
      const o = { x: source.x0 ?? source.x, y: source.y0 ?? source.y }
      return createCurvedPath(o, o)
    })

  // Update existing links
  const linkUpdate = linkEnter.merge(link)

  linkUpdate
    .transition()
    .duration(ANIMATION_DURATION)
    .attr('d', (d) => {
      const source = d.source as D3TreeNode
      const target = d.target as D3TreeNode
      return createCurvedPath(
        { x: source.x, y: source.y },
        { x: target.x, y: target.y }
      )
    })
    .attr('opacity', (d) => {
      const target = d.target as D3TreeNode
      return target.data.is_active ? 1 : 0.3
    })

  // Remove old links
  link.exit().transition().duration(ANIMATION_DURATION).attr('opacity', 0).remove()

  // Update nodes
  const node = g
    .selectAll<SVGGElement, D3TreeNode>('.node')
    .data(nodes, (d) => d.data.id)

  // Enter new nodes
  const nodeEnter = node
    .enter()
    .append('g')
    .attr('class', 'node')
    .attr('transform', (d) => {
      const x = d.x0 ?? d.x
      const y = d.y0 ?? d.y
      return `translate(${x},${y})`
    })
    .style('opacity', 0)

  // Add circles to nodes
  nodeEnter
    .append('circle')
    .attr('r', 10)
    .attr('fill', (d) => {
      const agentName = d.data.agent_name
      return getAgentColor(agentName)
    })
    .attr('stroke', '#ffffff')
    .attr('stroke-width', 1.5)
    .style('cursor', 'pointer')

  // Add labels to nodes
  const label = nodeEnter.append('g').attr('class', 'label')

  // Add a background rect for the text
  label
    .append('rect')
    .style('fill', '#2a2a2e')
    .style('stroke', '#444')
    .style('stroke-width', 1)
    .style('rx', 3)
    .style('ry', 3)

  label
    .append('text')
    .attr('dy', '0.31em')
    .attr('x', (d) => (d.children || d._children ? -25 : 25))
    .attr('text-anchor', (d) => (d.children || d._children ? 'end' : 'start'))
    .text((d) => d.data.agent_name)
    .style('fill', '#c9d1d9')
    .style('font-size', '12px')
    .style('font-family', 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif')
    .each(function () {
      const bbox = this.getBBox()
      const padding = 5
      const rect = d3.select(this.parentNode as SVGGElement).select('rect')
      rect
        .attr('x', bbox.x - padding)
        .attr('y', bbox.y - padding)
        .attr('width', bbox.width + padding * 2)
        .attr('height', bbox.height + padding * 2)
    })

  // Add tool badges
  const toolBadgeContainer = nodeEnter
    .append('g')
    .attr('class', 'tool-badges')
    .attr('transform', (d) => {
      const isLeft = d.children || d._children
      // Position below the agent name label (y=20 for below)
      const xOffset = isLeft ? -25 : 25
      return `translate(${xOffset}, 20)`
    })

  // For each node, check if it has tool calls
  toolBadgeContainer.each(function(d) {
    const container = d3.select(this)
    const toolCall = toolCallsByNodeId[d.data.id]

    if (toolCall && toolCall.tools && toolCall.tools.length > 0) {
      // Check if tool execution has completed
      const toolExecution = toolExecutionsByNodeId[d.data.id]
      const isExecuting = !toolExecution

      // Create badges for each tool
      toolCall.tools.forEach((tool, index) => {
        const colors = getToolColor(tool.name)
        const badge = container.append('g')
          .attr('transform', `translate(0, ${index * 20})`)

        // Add background rect for the badge
        const badgeRect = badge
          .append('rect')
          .attr('rx', 8)
          .attr('ry', 8)
          .style('fill', colors.bg)
          .style('opacity', 0.9)
          .style('stroke', colors.border)
          .style('stroke-width', 1)

        // Add tool name
        const toolText = badge
          .append('text')
          .attr('text-anchor', 'start')
          .attr('dominant-baseline', 'middle')
          .style('fill', '#ffffff')
          .style('font-size', '10px')
          .style('font-family', 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif')
          .style('font-weight', '500')
          .text(tool.name)

        // Get text dimensions and position rect around it
        const bbox = (toolText.node() as SVGTextElement).getBBox()
        const padding = 4

        // Position text with padding
        toolText
          .attr('x', padding)
          .attr('y', bbox.height / 2 + padding)

        // Size and position rect to contain text
        badgeRect
          .attr('x', 0)
          .attr('y', 0)
          .attr('width', bbox.width + padding * 2)
          .attr('height', bbox.height + padding * 2)

        // Apply pulsing animation if still executing
        applyPulsingAnimation(badge, isExecuting)

        // Add click handler to show results when execution is complete
        if (!isExecuting) {
          badge
            .style('cursor', 'pointer')
            .on('click', function(event: MouseEvent) {
              event.stopPropagation()
              const execution = toolExecutionsByNodeId[d.data.id]
              if (execution && execution.results) {
                // Show results in console for now (will add modal later)
                console.log('=== Tool Execution Results ===')
                console.log('Agent:', execution.agent_name)
                execution.results.forEach((result: ToolExecutionResult, idx: number) => {
                  console.log(`\nTool ${idx + 1}: ${result.tool_name}`)
                  console.log('Success:', result.success)
                  console.log('Result:', result.result)
                })
              }
            })
        }
      })
    }
  })

  // Update existing nodes
  const nodeUpdate = nodeEnter.merge(node)

  nodeUpdate
    .transition()
    .duration(ANIMATION_DURATION)
    .attr('transform', (d) => `translate(${d.x},${d.y})`)
    .style('opacity', (d) => {
      const isActive = activeNodeIds.has(d.data.id)
      return d.data.is_active ? (isActive ? 1 : 0.6) : 0.3
    })

  nodeUpdate
    .select('circle')
    .attr('fill', (d: D3TreeNode) => getAgentColor(d.data.agent_name))
    .attr('stroke', (d: D3TreeNode) => {
      const isActive = activeNodeIds.has(d.data.id)
      return isActive ? '#58a6ff' : '#c9d1d9'
    })
    .attr('stroke-width', (d: D3TreeNode) => {
      const isActive = activeNodeIds.has(d.data.id)
      return isActive ? 3 : 2
    })

  // Update tool badges for existing nodes
  nodeUpdate.each(function(d) {
    const nodeElement = d3.select(this)
    const existingBadges = nodeElement.select('.tool-badges')

    // Clear existing badges
    existingBadges.selectAll('*').remove()

    // Re-add badges if tools exist
    const toolCall = toolCallsByNodeId[d.data.id]
    if (toolCall && toolCall.tools && toolCall.tools.length > 0) {
      // Check if tool execution has completed
      const toolExecution = toolExecutionsByNodeId[d.data.id]
      const isExecuting = !toolExecution

      toolCall.tools.forEach((tool, index) => {
        const colors = getToolColor(tool.name)
        const badge = existingBadges.append('g')
          .attr('transform', `translate(0, ${index * 20})`)

        const badgeRect = badge
          .append('rect')
          .attr('rx', 8)
          .attr('ry', 8)
          .style('fill', colors.bg)
          .style('opacity', 0.9)
          .style('stroke', colors.border)
          .style('stroke-width', 1)

        const toolText = badge
          .append('text')
          .attr('text-anchor', 'start')
          .attr('dominant-baseline', 'middle')
          .style('fill', '#ffffff')
          .style('font-size', '10px')
          .style('font-family', 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif')
          .style('font-weight', '500')
          .text(tool.name)

        const bbox = (toolText.node() as SVGTextElement).getBBox()
        const padding = 4

        // Position text with padding
        toolText
          .attr('x', padding)
          .attr('y', bbox.height / 2 + padding)

        // Size and position rect to contain text
        badgeRect
          .attr('x', 0)
          .attr('y', 0)
          .attr('width', bbox.width + padding * 2)
          .attr('height', bbox.height + padding * 2)

        // Apply pulsing animation if still executing
        applyPulsingAnimation(badge, isExecuting)

        // Add click handler to show results when execution is complete
        if (!isExecuting) {
          badge
            .style('cursor', 'pointer')
            .on('click', function(event: MouseEvent) {
              event.stopPropagation()
              const execution = toolExecutionsByNodeId[d.data.id]
              if (execution && execution.results) {
                // Show results in console for now (will add modal later)
                console.log('=== Tool Execution Results ===')
                console.log('Agent:', execution.agent_name)
                execution.results.forEach((result: ToolExecutionResult, idx: number) => {
                  console.log(`\nTool ${idx + 1}: ${result.tool_name}`)
                  console.log('Success:', result.success)
                  console.log('Result:', result.result)
                })
              }
            })
        }
      })
    }
  })

  // Remove old nodes
  const nodeExit = node.exit()

  nodeExit
    .transition()
    .duration(ANIMATION_DURATION)
    .attr('transform', () => {
      // Move exiting nodes to parent's position
      return `translate(${root.x ?? 0},${root.y ?? 0})`
    })
    .style('opacity', 0)
    .remove()

  // Store old positions for smooth transitions
  nodes.forEach((d) => {
    d.x0 = d.x
    d.y0 = d.y
  })
}

/**
 * Create a curved path for GitHub-style branch arrows.
 */
function createCurvedPath(
  source: { x: number; y: number },
  target: { x: number; y: number }
): string {
  const midX = (source.x + target.x) / 2

  return `M ${source.x} ${source.y}
          C ${midX} ${source.y},
            ${midX} ${target.y},
            ${target.x} ${target.y}`
}

/**
 * Get agent color based on agent name.
 */
function getAgentColor(agentName: string): string {
  const colorMap: Record<string, string> = {
    User_proxy: 'rgba(147, 51, 234, 0.4)',
    Developer: 'rgba(59, 130, 246, 0.4)',
    Planner: 'rgba(236, 72, 153, 0.4)',
    Executor: 'rgba(34, 197, 94, 0.4)',
    Quality_assurance: 'rgba(251, 146, 60, 0.4)',
    Web_search_agent: 'rgba(20, 184, 166, 0.4)',
    Report_writer: 'rgba(139, 92, 246, 0.4)',
    User: 'rgba(255, 255, 255, 0.4)',
    System: 'rgba(156, 163, 175, 0.4)',
  }

  return colorMap[agentName] ?? 'rgba(156, 163, 175, 0.4)'
}
