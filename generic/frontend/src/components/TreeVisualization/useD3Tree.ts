import { useEffect, useRef, useState, useCallback } from 'react'
import * as d3 from 'd3'
import type { TreeNode, ToolCall, ToolExecution, ToolExecutionResult} from "../../types"
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
    edgeInterrupt?: { targetNodeId: string; position: { x: number; y: number }; trimCount: number } | null
    onEdgeClick?: (targetNodeId: string, position: { x: number; y: number }) => void
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
    isNavigationMode: boolean
    enableAutoCenter: () => void
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
    const {
      width,
      height,
      config = {},
      toolCallsByNodeId = {},
      toolExecutionsByNodeId = {},
      isInterrupted = false,
      edgeInterrupt = null,
      onEdgeClick,
    } = options

    const svgRef = useRef<SVGSVGElement>(null)
    const gRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null)
    const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
    const transformRef = useRef<d3.ZoomTransform>(d3.zoomIdentity)
    const userInteractionTimeoutRef = useRef<number | null>(null)

    const [root, setRoot] = useState<D3TreeNode | null>(null)
    const [activeNodeIds, setActiveNodeIds] = useState<Set<string>>(new Set())
    const [centerNodeId, setCenterNodeId] = useState<string | null>(null)
    const [autoCenterEnabled, setAutoCenterEnabled] = useState<boolean>(true)
    const lastMouseActivityRef = useRef<number>(Date.now())
    const throttleTimeoutRef = useRef<number | null>(null)
    const isInitializedRef = useRef<boolean>(false)

    const treeConfig: TreeConfig = { ...DEFAULT_TREE_CONFIG, ...config }

    /**
     * Reset the auto-center timeout whenever user interacts with the tree.
     * This ensures auto-centering is disabled during active interaction
     * and only re-enables after 15 seconds of inactivity.
     * Throttled to avoid excessive calls during continuous movement.
     */
    const handleUserActivity = useCallback(() => {
      // Ignore activity during initial setup
      if (!isInitializedRef.current) {
        console.log('[useD3Tree] Ignoring activity during initialization')
        return
      }

      console.log('[useD3Tree] ⚠️ handleUserActivity called')
      const now = Date.now()

      // Throttle to max once per 100ms to avoid excessive state updates
      if (throttleTimeoutRef.current && now - lastMouseActivityRef.current < 100) {
        console.log('[useD3Tree] Throttled - ignoring')
        return
      }

      lastMouseActivityRef.current = now

      // Disable auto-centering immediately (only if not already disabled)
      setAutoCenterEnabled(prev => {
        if (prev) {
          console.log('[useD3Tree] 🔴 User activity detected - DISABLING auto-center')
          return false
        }
        console.log('[useD3Tree] Auto-center already disabled')
        return prev
      })

      // Clear any existing timeout
      if (userInteractionTimeoutRef.current) {
        clearTimeout(userInteractionTimeoutRef.current)
      }

      // Set a 15-second timeout to re-enable auto-centering
      userInteractionTimeoutRef.current = window.setTimeout(() => {
        console.log('[useD3Tree] 🟢 15 seconds of inactivity - re-enabling auto-center')
        setAutoCenterEnabled(true)
      }, 15000)
    }, [])
  
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

      // Setup zoom behavior - only track zoom START for user interaction
      const zoom = d3
        .zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 3])
        .on('zoom', (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
          g.attr('transform', event.transform.toString())
          transformRef.current = event.transform
        })
        .on('start', (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
          // Only trigger user activity if it's an actual user interaction (not programmatic)
          if (event.sourceEvent) {
            handleUserActivity()
          }
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

      // Track mouse drag specifically (mousedown + mousemove = drag)
      const svgElement = svgRef.current
      let isDragging = false

      const handleMouseDown = () => {
        isDragging = true
      }

      const handleMouseMove = () => {
        if (isDragging) {
          handleUserActivity()
        }
      }

      const handleMouseUp = () => {
        isDragging = false
      }

      // Only track wheel events (scroll to zoom)
      const handleWheel = () => {
        handleUserActivity()
      }

      svgElement.addEventListener('mousedown', handleMouseDown)
      svgElement.addEventListener('mousemove', handleMouseMove)
      svgElement.addEventListener('mouseup', handleMouseUp)
      svgElement.addEventListener('wheel', handleWheel)

      // Mark as initialized after a short delay to avoid capturing setup events
      setTimeout(() => {
        isInitializedRef.current = true
        console.log('[useD3Tree] ✅ Initialization complete - user activity tracking enabled')
      }, 500)

      // Cleanup function - runs when component unmounts or dependencies change
      return () => {
        if (userInteractionTimeoutRef.current) {
          clearTimeout(userInteractionTimeoutRef.current)
        }
        svgElement.removeEventListener('mousedown', handleMouseDown)
        svgElement.removeEventListener('mousemove', handleMouseMove)
        svgElement.removeEventListener('mouseup', handleMouseUp)
        svgElement.removeEventListener('wheel', handleWheel)
        isInitializedRef.current = false
      }
    }, [treeData, currentBranchId, width, height, handleUserActivity])
  
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
        edgeInterrupt,
        onEdgeClick,
      })

      // After tree updates, preserve transform in navigation mode
      if (!autoCenterEnabled && svgRef.current && zoomRef.current) {
        console.log('[useD3Tree] Tree updated in navigation mode - re-applying transform')
        const svg = d3.select(svgRef.current)
        // Use a very short timeout to let D3 finish its update first
        setTimeout(() => {
          svg.call(zoomRef.current!.transform, transformRef.current)
        }, 0)
      }
    }, [root, activeNodeIds, width, height, treeConfig, toolCallsByNodeId, toolExecutionsByNodeId, edgeInterrupt, onEdgeClick, autoCenterEnabled])
  
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
        // Calculate transform to position the node optimally
        const svg = d3.select(svgRef.current)
        const scale = transformRef.current.k

        // Center horizontally
        const x = -targetNode.x! * scale + width / 2

        // Position vertically at 1/3 from bottom (2/3 from top)
        // This shows more tree context above the new node, which is better
        // for viewing new messages at the bottom of the tree
        const y = -targetNode.y! * scale + (height * 2 / 3)

        console.log(`[useD3Tree] Centering to position: x=${x}, y=${y}, scale=${scale}`)

        svg
          .transition()
          .duration(ANIMATION_DURATION)
          .call(zoomRef.current.transform, d3.zoomIdentity.translate(x, y).scale(scale))
      }
    }, [root, width, height, centerNodeId])
  
    /**
     * Automatically recenter the view when the centerNodeId changes.
     * Only if auto-centering is enabled and not interrupted.
     * If in navigation mode, preserve the current transform.
     */
    useEffect(() => {
      if (centerNodeId && autoCenterEnabled && !isInterrupted) {
        recenter()
      } else if (!autoCenterEnabled && svgRef.current && zoomRef.current) {
        // In navigation mode: preserve the current transform when tree updates
        console.log('[useD3Tree] Navigation mode - preserving current transform')
        const svg = d3.select(svgRef.current)
        const currentTransform = transformRef.current

        // Re-apply the current transform (without animation to avoid jarring movement)
        svg.call(zoomRef.current.transform, currentTransform)
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

    /**
     * Manually enable auto-centering (exit navigation mode).
     */
    const enableAutoCenter = useCallback(() => {
      console.log('[useD3Tree] Manually enabling auto-center')

      // Clear any existing timeout
      if (userInteractionTimeoutRef.current) {
        clearTimeout(userInteractionTimeoutRef.current)
        userInteractionTimeoutRef.current = null
      }

      // Enable auto-centering
      setAutoCenterEnabled(true)

      // Immediately recenter to the last message node
      if (centerNodeId) {
        setTimeout(() => recenter(), 0)
      }
    }, [centerNodeId, recenter])

    // Log navigation mode state for debugging
    console.log('[useD3Tree] Current state:', {
      autoCenterEnabled,
      isNavigationMode: !autoCenterEnabled,
      centerNodeId
    })

    return {
      svgRef,
      root,
      activeNodeIds,
      centerNodeId,
      recenter,
      zoomIn,
      zoomOut,
      resetZoom,
      isNavigationMode: !autoCenterEnabled,
      enableAutoCenter,
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
    edgeInterrupt?: { targetNodeId: string; position: { x: number; y: number } } | null
    onEdgeClick?: (targetNodeId: string, position: { x: number; y: number }) => void
  }
  
  function updateTree(
    root: D3TreeNode,
    g: d3.Selection<SVGGElement, unknown, null, undefined>,
    options: UpdateTreeOptions
  ): void {
    const {
      width,
      height,
      config,
      activeNodeIds,
      toolCallsByNodeId,
      toolExecutionsByNodeId,
      edgeInterrupt,
      onEdgeClick,
    } = options

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
      .attr('stroke-width', 3)
      .style('cursor', (d) => {
        const target = d.target as D3TreeNode
        return target.data.is_active ? 'pointer' : 'default'
      })
      .style('transition', 'stroke-width 0.2s ease-in-out')
      .attr('d', (d) => {
        const source = d.source as D3TreeNode
        const o = { x: source.x0 ?? source.x, y: source.y0 ?? source.y }
        return createCurvedPath(o, o)
      })
      .on('mouseenter', function(this: SVGPathElement, event: MouseEvent, d: d3.HierarchyPointLink<TreeNode>) {
        const target = d.target as D3TreeNode
        if (target.data.is_active) {
          // Immediate jump to 4px
          d3.select(this).attr('stroke-width', 4)
          // Then smoothly transition to 6px
          d3.select(this)
            .transition()
            .duration(150)
            .attr('stroke-width', 6)
        }
      })
      .on('mouseleave', function(this: SVGPathElement, event: MouseEvent, d: d3.HierarchyPointLink<TreeNode>) {
        const target = d.target as D3TreeNode
        const isInterrupting = edgeInterrupt && edgeInterrupt.targetNodeId === target.data.id
        d3.select(this)
          .transition()
          .duration(200)
          .attr('stroke-width', isInterrupting ? 4 : 3)
      })
      .on('click', function(event: MouseEvent, d: d3.HierarchyPointLink<TreeNode>) {
        const target = d.target as D3TreeNode
        // Only allow clicking on active branch edges
        if (onEdgeClick && target.data.is_active) {
          event.stopPropagation()

          // Use the mouse event position directly - these are screen coordinates
          // which we'll convert to container-relative coordinates in the handler
          onEdgeClick(target.data.id, { x: event.clientX, y: event.clientY })
        }
      })
  
    // Update existing links
    const linkUpdate = linkEnter.merge(link)

    // Apply non-animated styles and event handlers BEFORE transition
    linkUpdate
      .style('cursor', (d) => {
        const target = d.target as D3TreeNode
        return target.data.is_active ? 'pointer' : 'default'
      })
      .on('mouseenter', function(this: SVGPathElement, event: MouseEvent, d: d3.HierarchyPointLink<TreeNode>) {
        const target = d.target as D3TreeNode
        if (target.data.is_active) {
          // Immediate jump to 4px
          d3.select(this).attr('stroke-width', 4)
          // Then smoothly transition to 6px
          d3.select(this)
            .transition()
            .duration(150)
            .attr('stroke-width', 6)
        }
      })
      .on('mouseleave', function(this: SVGPathElement, event: MouseEvent, d: d3.HierarchyPointLink<TreeNode>) {
        const target = d.target as D3TreeNode
        const isInterrupting = edgeInterrupt && edgeInterrupt.targetNodeId === target.data.id
        d3.select(this)
          .transition()
          .duration(200)
          .attr('stroke-width', isInterrupting ? 4 : 3)
      })
      .on('click', function(event: MouseEvent, d: d3.HierarchyPointLink<TreeNode>) {
        const target = d.target as D3TreeNode
        // Only allow clicking on active branch edges
        if (onEdgeClick && target.data.is_active) {
          event.stopPropagation()

          // Use the mouse event position directly - these are screen coordinates
          // which we'll convert to container-relative coordinates in the handler
          onEdgeClick(target.data.id, { x: event.clientX, y: event.clientY })
        }
      })

    // Apply animated attributes with transition
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
      .attr('stroke', (d) => {
        const target = d.target as D3TreeNode
        // If this edge is being interrupted, color it red
        if (edgeInterrupt && edgeInterrupt.targetNodeId === target.data.id) {
          return '#ef4444' // red color for interrupting edge
        }
        return '#30363d' // default color
      })
      .attr('stroke-width', (d) => {
        const target = d.target as D3TreeNode
        // If this edge is being interrupted, make it thicker
        if (edgeInterrupt && edgeInterrupt.targetNodeId === target.data.id) {
          return 4
        }
        return 3
      })
  
    // Remove old links
    link.exit().transition().duration(ANIMATION_DURATION).attr('opacity', 0).remove()

    // Add "interrupting..." label to the edge being interrupted
    const interruptLabel = g
      .selectAll<SVGTextElement, d3.HierarchyPointLink<TreeNode>>('.interrupt-label')
      .data(
        edgeInterrupt
          ? links.filter((d) => (d.target as D3TreeNode).data.id === edgeInterrupt.targetNodeId)
          : [],
        (d: d3.HierarchyPointLink<TreeNode>) => (d.target as D3TreeNode).data.id
      )

    // Enter new labels
    const interruptLabelEnter = interruptLabel
      .enter()
      .append('text')
      .attr('class', 'interrupt-label')
      .style('fill', '#ef4444')
      .style('font-size', '12px')
      .style('font-weight', 'bold')
      .style('pointer-events', 'none')
      .text('interrupting...')

    // Update existing labels
    const interruptLabelUpdate = interruptLabelEnter.merge(interruptLabel)

    interruptLabelUpdate
      .attr('x', (d: d3.HierarchyPointLink<TreeNode>) => {
        const source = d.source as D3TreeNode
        const target = d.target as D3TreeNode
        return (source.x + target.x) / 2 + 10
      })
      .attr('y', (d: d3.HierarchyPointLink<TreeNode>) => {
        const source = d.source as D3TreeNode
        const target = d.target as D3TreeNode
        return (source.y + target.y) / 2
      })

    // Remove old labels
    interruptLabel.exit().remove()

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
          const colors = getToolColor()
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
          const colors = getToolColor()
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
  