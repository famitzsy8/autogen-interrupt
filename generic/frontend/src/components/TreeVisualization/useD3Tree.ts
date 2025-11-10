import { useEffect, useRef, useState, useCallback } from 'react'
import * as d3 from 'd3'
import type { ConversationItemType, TreeNode, ToolCall, ToolExecution } from "../../types"
import type { D3TreeNode, TreeConfig } from './utils/treeUtils'
import {
    convertToD3Hierarchy,
    findActivePath,
    findVisibleNodes,
    expandAllNodes,
    findLastMessageNode,
    DEFAULT_TREE_CONFIG,
  } from './utils/treeUtils'

interface UseD3TreeOptions {
    width: number
    height: number
    config?: Partial<TreeConfig>
    toolCallsByNodeId?: Record<string, ToolCall>
    toolExecutionsByNodeId?: Record<string, ToolExecution>
    isInterrupted?: boolean
    onNodeClick?: (nodeId: string, itemType: ConversationItemType) => void
}

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
          .style('opacity', 0.2)
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
 * Get fixed color for tool badges.
 */
function getToolColor(): { bg: string; border: string } {
  return { bg: '#1f6feb', border: '#58a6ff' }
}

function getConversationItemTypeForNode(node: TreeNode): ConversationItemType {
  if (node.node_type === 'tool_call') return 'tool_call'
  if (node.node_type === 'tool_execution') return 'tool_execution'
  return 'message'
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
    const { width, height, config = {}, toolCallsByNodeId = {}, toolExecutionsByNodeId = {}, isInterrupted = false, onNodeClick } = options

    const svgRef = useRef<SVGSVGElement>(null)
    const gRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null)
    const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
    const transformRef = useRef<d3.ZoomTransform>(d3.zoomIdentity)
    const userInteractionTimeoutRef = useRef<number | null>(null)

    const [root, setRoot] = useState<D3TreeNode | null>(null)
    const [activeNodeIds, setActiveNodeIds] = useState<Set<string>>(new Set())
    const [centerNodeId, setCenterNodeId] = useState<string | null>(null)
    const [autoCenterEnabled, setAutoCenterEnabled] = useState<boolean>(true)
  
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
  
      // Setup zoom behavior with user interaction tracking
      const zoom = d3
        .zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 3])
        .on('zoom', (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
          g.attr('transform', event.transform.toString())
          transformRef.current = event.transform
        })
        .on('start', () => {
          // User started interacting with the tree (pan/zoom)
          // Disable auto-centering
          setAutoCenterEnabled(false)

          // Clear any existing timeout
          if (userInteractionTimeoutRef.current) {
            clearTimeout(userInteractionTimeoutRef.current)
          }

          // Set a 15-second timeout to re-enable auto-centering
          userInteractionTimeoutRef.current = setTimeout(() => {
            setAutoCenterEnabled(true)
          }, 15000)
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
  
      // Find last message node to center on
      const lastMessageNode = findLastMessageNode(hierarchy, currentBranchId)
      if (lastMessageNode) {
        setCenterNodeId(lastMessageNode.data.id)
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
        toolCallsByNodeId,
        toolExecutionsByNodeId,
        onNodeClick,
      })
    }, [root, activeNodeIds, width, height, treeConfig, toolCallsByNodeId, toolExecutionsByNodeId, onNodeClick])
  
    /**
     * Update center node when tree data changes to keep view on latest messages.
     * Only auto-center if:
     * - Not interrupted
     * - Auto-centering is enabled (user hasn't interacted recently)
     */
    useEffect(() => {
      console.log('[useD3Tree] Recentering effect triggered', {
        hasRoot: !!root,
        isInterrupted,
        autoCenterEnabled,
        currentCenterNodeId: centerNodeId
      })

      if (!root || isInterrupted || !autoCenterEnabled) {
        console.log('[useD3Tree] Skipping recenter - conditions not met')
        return
      }

      const lastMessageNode = findLastMessageNode(root, currentBranchId)
      if (lastMessageNode && lastMessageNode.data.id !== centerNodeId) {
        console.log(`[useD3Tree] Updating center node to: ${lastMessageNode.data.id} (type: ${lastMessageNode.data.node_type})`)
        setCenterNodeId(lastMessageNode.data.id)
      } else {
        console.log('[useD3Tree] No center node update needed')
      }
    }, [root, centerNodeId, currentBranchId, isInterrupted, autoCenterEnabled])
  
    /**
     * Recenter the view on the specified center node or root.
     */
    const recenter = useCallback(() => {
      if (!root || !svgRef.current || !zoomRef.current) return

      // Find the target node by centerNodeId if provided
      let targetNode: D3TreeNode | null = null
      if (centerNodeId) {
        root.each((node) => {
          if (node.data.id === centerNodeId) {
            targetNode = node
          }
        })
      }

      // Fallback to root if node not found
      if (!targetNode) {
        targetNode = root
      }

      if (targetNode) {
        console.log(`[useD3Tree] Recentering view to node: ${targetNode.data.id} at (${targetNode.x}, ${targetNode.y})`)
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
    }, [root, width, height, centerNodeId])
  
    /**
     * Automatically recenter the view when the centerNodeId changes.
     * Only if auto-centering is enabled and not interrupted.
     */
    useEffect(() => {
      if (centerNodeId && autoCenterEnabled && !isInterrupted) {
        recenter()
      }
    }, [centerNodeId, recenter, autoCenterEnabled, isInterrupted])

    /**
     * Cleanup timeout on unmount.
     */
    useEffect(() => {
      return () => {
        if (userInteractionTimeoutRef.current) {
          clearTimeout(userInteractionTimeoutRef.current)
        }
      }
    }, [])
  
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
    toolCallsByNodeId: Record<string, ToolCall>
    toolExecutionsByNodeId: Record<string, ToolExecution>
    onNodeClick?: (nodeId: string, itemType: ConversationItemType) => void
  }

  function updateTree(
    root: D3TreeNode,
    g: d3.Selection<SVGGElement, unknown, null, undefined>,
    options: UpdateTreeOptions
  ): void {
    const { width, height, config, activeNodeIds, toolCallsByNodeId, toolExecutionsByNodeId, onNodeClick } = options

    // Expand all nodes to show full tree
    expandAllNodes(root)
  
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
  
    // Agent name in box (always on left, more distant from node)
    label
      .append('text')
      .attr('dy', '0.31em')
      .attr('x', -35)
      .attr('text-anchor', 'end')
      .text((d) => d.data.agent_name)
      .style('fill', '#c9d1d9')
      .style('font-size', '11px')
      .style('font-family', 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif')
      .style('cursor', 'pointer')
      .on('click', function(event: MouseEvent, d: D3TreeNode) {
        event.stopPropagation()
        if (onNodeClick) {
          onNodeClick(d.data.id, getConversationItemTypeForNode(d.data))
        }
      })
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

    // Summary text on right (no box, grey text, max 3 lines, ~500 chars)
    label
      .append('foreignObject')
      .attr('x', 25)
      .attr('y', -18)
      .attr('width', 400)
      .attr('height', 50)
      .style('overflow', 'visible')
      .append('xhtml:div')
      .style('color', '#8b949e')
      .style('font-size', '10px')
      .style('font-family', 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif')
      .style('line-height', '1.3')
      .style('display', '-webkit-box')
      .style('-webkit-line-clamp', '3')
      .style('-webkit-box-orient', 'vertical')
      .style('overflow', 'hidden')
      .style('text-overflow', 'ellipsis')
      .style('word-wrap', 'break-word')
      .style('cursor', 'pointer')
      .text((d) => d.data.summary || '')
      .on('click', function(event: MouseEvent, d: D3TreeNode) {
        console.log('[useD3Tree] Summary clicked:', d.data.id, 'type:', d.data.node_type)
        event.stopPropagation()
        if (onNodeClick) {
          onNodeClick(d.data.id, getConversationItemTypeForNode(d.data))
        }
      })
  
    // Add tool badges
    const toolBadgeContainer = nodeEnter
      .append('g')
      .attr('class', 'tool-badges')
      .attr('transform', 'translate(35, -8)') // Position on the right, aligned with summary
  
    // For each node, check if it has tool calls
    toolBadgeContainer.each(function(d) {
      const container = d3.select(this)
      const toolCall = toolCallsByNodeId[d.data.id]
  
      if (toolCall && toolCall.tools && toolCall.tools.length > 0) {
        // Check if tool execution has completed
        const toolExecution = toolExecutionsByNodeId[d.data.id]
        const isExecuting = !toolExecution

        // Track horizontal position for badges
        let xPosition = 0

        // Create badges for each tool (arranged horizontally, max 6)
        const toolsToShow = toolCall.tools.slice(0, 6)
        toolsToShow.forEach((tool) => {
          const colors = getToolColor()
          const badge = container.append('g')
            .attr('transform', `translate(${xPosition}, 0)`)
  
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

          // Update horizontal position for next badge
          xPosition += bbox.width + padding * 2 + 5 // 5px gap between badges

          // Apply pulsing animation if still executing
          applyPulsingAnimation(badge, isExecuting)

          // TODO: Add click handler for tool badges to navigate to tool call details
          // See TOOL_CLICKING_FEATURE_DOCUMENTATION.md for implementation details
          // badge.style('cursor', 'pointer').on('click', function(event: MouseEvent) { ... })
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

        // Track horizontal position for badges
        let xPosition = 0

        // Limit to max 6 tools arranged horizontally
        const toolsToShow = toolCall.tools.slice(0, 6)
        toolsToShow.forEach((tool) => {
          const colors = getToolColor()
          const badge = existingBadges.append('g')
            .attr('transform', `translate(${xPosition}, 0)`)
  
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

          // Update horizontal position for next badge
          xPosition += bbox.width + padding * 2 + 5 // 5px gap between badges

          // Apply pulsing animation if still executing
          applyPulsingAnimation(badge, isExecuting)

          // TODO: Add click handler for tool badges to navigate to tool call details
          // See TOOL_CLICKING_FEATURE_DOCUMENTATION.md for implementation details
          // badge.style('cursor', 'pointer').on('click', function(event: MouseEvent) { ... })
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
  