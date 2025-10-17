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
import type { TreeNode } from '../../types'
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
  const { width, height, config = {}, maxVisibleHeight = 30 } = options

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
    })
  }, [root, activeNodeIds, centerNodeId, width, height, maxVisibleHeight, treeConfig])

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
}

function updateTree(
  root: D3TreeNode,
  g: d3.Selection<SVGGElement, unknown, null, undefined>,
  options: UpdateTreeOptions
): void {
  const { width, height, config, activeNodeIds, centerNodeId, maxVisibleHeight } = options

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
    Jara_Supporter: 'rgba(239, 68, 68, 0.4)',
    Kast_Supporter: 'rgba(59, 130, 246, 0.4)',
    Neural_Agent: 'rgba(168, 85, 247, 0.4)',
    Moderate_Left: 'rgba(125, 211, 252, 0.4)',
    Moderate_Right: 'rgba(251, 146, 60, 0.4)',
    User: 'rgba(255, 255, 255, 0.4)',
    System: 'rgba(156, 163, 175, 0.4)',
  }

  return colorMap[agentName] ?? 'rgba(156, 163, 175, 0.4)'
}
