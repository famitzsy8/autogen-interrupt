import { useEffect, useRef, useState, useCallback } from 'react'
import * as d3 from 'd3'
import type { ConversationItemType, TreeNode, ToolCall, ToolExecution, AnalysisComponent, AnalysisScores } from "../../types"
import type { D3TreeNode, TreeConfig } from './utils/treeUtils'
import {
  convertToD3Hierarchy,
  findActivePath,
  expandAllNodes,
  findLastMessageNode,
  DEFAULT_TREE_CONFIG,
  extractAgentNames,
} from './utils/treeUtils'

interface UseD3TreeOptions {
  width: number
  height: number
  config?: Partial<TreeConfig>
  toolCallsByNodeId?: Record<string, ToolCall>
  toolExecutionsByNodeId?: Record<string, ToolExecution>
  isInterrupted?: boolean
  onNodeClick?: (nodeId: string, itemType: ConversationItemType) => void
  edgeInterrupt?: { targetNodeId: string; position: { x: number; y: number }; trimCount: number } | null
  onEdgeClick?: (targetNodeId: string, position: { x: number; y: number }, trimCount: number) => void
  analysisComponents?: AnalysisComponent[]
  analysisScores?: Map<string, AnalysisScores>
  triggeredNodes?: Set<string>
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

// Swimlane layout constants for horizontal visualization
const SWIMLANE_HEIGHT = 120          // Height of each agent swimlane in pixels
const NODE_HORIZONTAL_SPACING = 200  // Horizontal distance between depth levels
const LEFT_MARGIN = 150              // Left margin before first nodes
const NODE_RADIUS = 8                // Radius of node circles

// Dynamic spacing parameters
const RECENT_NODE_MAX_SPACING = 300  // Maximum spacing for the most recent nodes
const RECENT_NODE_MIN_SPACING = 150  // Minimum spacing for recent nodes (within 5 nodes)
const OLD_NODE_SPACING = 80          // Fixed spacing for older nodes (5+ positions back)
const RECENT_NODE_THRESHOLD = 5      // Number of nodes considered "recent"


function getConversationItemTypeForNode(node: TreeNode): ConversationItemType {
  if (node.node_type === 'tool_call') return 'tool_call'
  if (node.node_type === 'tool_execution') return 'tool_execution'
  return 'message'
}

/**
 * Calculate number of nodes to trim when branching at a given edge.
 * Trim count = number of active nodes in current branch AFTER the target node.
 */
function calculateTrimCount(targetNodeId: string, treeRoot: TreeNode): number {
  let count = 0
  let foundTarget = false

  function traverse(node: TreeNode): void {
    // If we already found the target, count this active node
    if (foundTarget && node.id !== targetNodeId && node.is_active) {
      count++
    }

    // Check if this is the target node
    if (node.id === targetNodeId) {
      foundTarget = true
    }

    // Traverse children
    if (node.children && node.children.length > 0) {
      node.children.forEach(child => traverse(child))
    }
  }

  traverse(treeRoot)
  return count
}

/**
 * Calculate dynamic spacing for a node based on its distance from the latest node.
 * - Last 2 nodes: maximum spacing (300px)
 * - Nodes 3-5 back: linearly decreasing spacing (150-300px)
 * - Nodes 5+ back: fixed small spacing (80px)
 *
 * @param distanceFromLatest - How many positions back from the latest node (0 = latest)
 * @returns Spacing in pixels to use after this node
 */
function calculateDynamicSpacing(distanceFromLatest: number): number {
  if (distanceFromLatest === 0) {
    return RECENT_NODE_MAX_SPACING
  }

  if (distanceFromLatest === 1) {
    return RECENT_NODE_MAX_SPACING
  }

  if (distanceFromLatest < RECENT_NODE_THRESHOLD) {
    const progressionRatio = (RECENT_NODE_THRESHOLD - distanceFromLatest) / (RECENT_NODE_THRESHOLD - 2)
    return RECENT_NODE_MIN_SPACING + (RECENT_NODE_MAX_SPACING - RECENT_NODE_MIN_SPACING) * progressionRatio
  }

  return OLD_NODE_SPACING
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
    onNodeClick,
    analysisComponents = [],
    analysisScores = new Map(),
    triggeredNodes = new Set(),
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
      return
    }

    const now = Date.now()

    // Throttle to max once per 100ms to avoid excessive state updates
    if (throttleTimeoutRef.current && now - lastMouseActivityRef.current < 100) {
      return
    }

    lastMouseActivityRef.current = now

    // Disable auto-centering immediately (only if not already disabled)
    setAutoCenterEnabled(prev => {
      if (prev) {
        return false
      }
      return prev
    })

    // Clear any existing timeout
    if (userInteractionTimeoutRef.current) {
      clearTimeout(userInteractionTimeoutRef.current)
    }

    // Set a 15-second timeout to re-enable auto-centering
    userInteractionTimeoutRef.current = window.setTimeout(() => {
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

    // Setup zoom behavior - optimized for horizontal swimlane layout
    // Scale extent [0.5, 3] allows 50% zoom out to 300% zoom in
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 3])
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
      onNodeClick,
      treeData,
      analysisComponents,
      analysisScores,
      triggeredNodes,
    })

    // After tree updates, preserve transform in navigation mode
    if (!autoCenterEnabled && svgRef.current && zoomRef.current) {
      const svg = d3.select(svgRef.current)
      // Use a very short timeout to let D3 finish its update first
      setTimeout(() => {
        svg.call(zoomRef.current!.transform, transformRef.current)
      }, 0)
    }
  }, [root, activeNodeIds, width, height, treeConfig, toolCallsByNodeId, toolExecutionsByNodeId, edgeInterrupt, onEdgeClick, autoCenterEnabled, onNodeClick, analysisComponents, analysisScores, triggeredNodes])

  /**
   * Update center node when tree data changes to keep view on latest messages.
   * Only auto-center if:
   * - Not interrupted
   * - Auto-centering is enabled (user hasn't interacted recently)
   */
  useEffect(() => {
    if (!root || isInterrupted || !autoCenterEnabled) {
      return
    }

    const lastMessageNode = findLastMessageNode(root, currentBranchId)
    if (lastMessageNode && lastMessageNode.data.id !== centerNodeId) {
      setCenterNodeId(lastMessageNode.data.id)
    }
  }, [root, centerNodeId, currentBranchId, isInterrupted, autoCenterEnabled])

  /**
   * Recenter the view on the rightmost (most recent) node.
   * For horizontal layout: pan to show the latest message on the right side,
   * while keeping all agent swimlanes vertically centered in view.
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
      // Calculate transform to position the node optimally for horizontal layout
      const svg = d3.select(svgRef.current)
      const scale = transformRef.current.k

      // Extract agent names to calculate total height
      const rawAgentNames = extractAgentNames(root.data)

      // Normalize for swimlane count
      const swimlaneNamesSet = new Set<string>()
      rawAgentNames.forEach(name => {
        const lower = name.toLowerCase()
        if (lower === 'you' || lower === 'user' || lower.includes('user_proxy') || lower.includes('userproxy')) {
          swimlaneNamesSet.add('User')
        } else {
          swimlaneNamesSet.add(name)
        }
      })

      const totalTreeHeight = swimlaneNamesSet.size * SWIMLANE_HEIGHT

      // Position rightmost node at 70% from left (show some context on right)
      // This allows users to see the most recent message while having room
      // to see what comes after it
      const x = -targetNode.x! * scale + (width * 0.7)

      // Keep swimlanes vertically centered
      const y = (height - totalTreeHeight * scale) / 2

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
   * Reset zoom to fit all agent swimlanes in viewport.
   * For horizontal layout: zoom to show all agents vertically,
   * and position view at left margin to show earliest messages.
   */
  const resetZoom = useCallback(() => {
    if (!svgRef.current || !zoomRef.current || !root) return

    const svg = d3.select(svgRef.current)

    // Extract agent names to calculate total height needed
    const rawAgentNames = extractAgentNames(root.data)

    // Normalize for swimlane count
    const swimlaneNamesSet = new Set<string>()
    rawAgentNames.forEach(name => {
      const lower = name.toLowerCase()
      if (lower === 'you' || lower === 'user' || lower.includes('user_proxy') || lower.includes('userproxy')) {
        swimlaneNamesSet.add('User')
      } else {
        swimlaneNamesSet.add(name)
      }
    })

    const totalTreeHeight = swimlaneNamesSet.size * SWIMLANE_HEIGHT

    // Calculate zoom scale to fit all agents in viewport height
    // Leave some padding (80% of viewport height for tree content)
    const zoomScale = Math.min(
      (height * 0.8) / totalTreeHeight,
      3 // Don't zoom in more than 3x
    )

    // Position at left margin horizontally, centered vertically
    const translateX = LEFT_MARGIN / 2
    const translateY = (height - totalTreeHeight * zoomScale) / 2

    svg
      .transition()
      .duration(ANIMATION_DURATION)
      .call(zoomRef.current.transform, d3.zoomIdentity.translate(translateX, translateY).scale(zoomScale))
  }, [height, root])

  /**
   * Manually enable auto-centering (exit navigation mode).
   */
  const enableAutoCenter = useCallback(() => {

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
  onNodeClick?: (nodeId: string, itemType: ConversationItemType) => void
  edgeInterrupt?: { targetNodeId: string; position: { x: number; y: number }; trimCount: number } | null
  onEdgeClick?: (targetNodeId: string, position: { x: number; y: number }, trimCount: number) => void
  treeData?: TreeNode | null
  analysisComponents: AnalysisComponent[]
  analysisScores: Map<string, AnalysisScores>
  triggeredNodes: Set<string>
}

/**
 * A tree node with calculated X,Y position in swimlane layout.
 */
interface PositionedNode {
  node: D3TreeNode   // Original D3 hierarchy node
  x: number          // Horizontal position (depth-based)
  y: number          // Vertical position (swimlane-based)
}

/**
 * An edge representing a parent-child relationship in the tree.
 */
interface Edge {
  source: PositionedNode     // Parent node
  target: PositionedNode     // Child node
  sourceX: number            // Pre-computed source X
  sourceY: number            // Pre-computed source Y
  targetX: number            // Pre-computed target X
  targetY: number            // Pre-computed target Y
}

function updateTree(
  root: D3TreeNode,
  g: d3.Selection<SVGGElement, unknown, null, undefined>,
  options: UpdateTreeOptions
): void {
  const {
    edgeInterrupt,
    onEdgeClick,
    onNodeClick,
    treeData,
    analysisComponents,
    analysisScores,
    triggeredNodes,
  } = options

  // Expand all nodes to show full tree
  expandAllNodes(root)

  // ============================================================
  // PHASE 1: DATA PREPARATION
  // ============================================================

  // Extract unique agent names from tree
  const rawAgentNames: string[] = extractAgentNames(root.data)

  // Normalize agent names for swimlane grouping
  // "You", "User", "UserProxy", "user_proxy" -> "User"
  const normalizeAgentName = (name: string): string => {
    const lower = name.toLowerCase()
    if (lower === 'you' || lower === 'user' || lower.includes('user_proxy') || lower.includes('userproxy')) {
      return 'User'
    }
    return name
  }

  // Collect unique swimlanes with their display names
  // Maps normalized agent_name -> display_name for swimlane labels
  const swimlaneDisplayNames = new Map<string, string>()
  const swimlaneNamesSet = new Set<string>()

  // Traverse tree to collect agent names and their display names
  function collectSwimlaneInfo(node: TreeNode): void {
    const normalized = normalizeAgentName(node.agent_name)
    swimlaneNamesSet.add(normalized)

    // Store display name for this normalized swimlane (prefer display_name over agent_name)
    if (!swimlaneDisplayNames.has(normalized)) {
      swimlaneDisplayNames.set(normalized, node.display_name || normalized)
    }

    if (node.children && node.children.length > 0) {
      node.children.forEach(child => collectSwimlaneInfo(child))
    }
  }

  collectSwimlaneInfo(root.data)

  const swimlaneNames = Array.from(swimlaneNamesSet).sort()

  // Create swimlane Y-map (mapping normalized name to Y position)
  const swimlaneYMap = new Map<string, number>()
  swimlaneNames.forEach((name, index) => {
    const y = index * SWIMLANE_HEIGHT + (SWIMLANE_HEIGHT / 2)
    swimlaneYMap.set(name, y)
  })

  // Create a map from original agent name to Y position
  const agentYMap = new Map<string, number>()
  rawAgentNames.forEach(name => {
    const normalized = normalizeAgentName(name)
    const y = swimlaneYMap.get(normalized)
    if (y !== undefined) {
      agentYMap.set(name, y)
    }
  })

  // Calculate maximum depth across ALL nodes (not just active branch)
  // This ensures we have X positions for all nodes, including new branches
  let maxDepth = 0
  let maxActiveDepth = 0
  root.each((node: D3TreeNode) => {
    if (node.depth > maxDepth) {
      maxDepth = node.depth
    }
    if (node.data.is_active && node.depth > maxActiveDepth) {
      maxActiveDepth = node.depth
    }
  })

  // Build depth-to-spacing map for ALL depths to handle branches
  const depthSpacingMap = new Map<number, number>()
  for (let depth = 0; depth <= maxDepth; depth++) {
    // Use distance from maxActiveDepth for spacing calculation to maintain visual hierarchy
    const distanceFromLatest = Math.max(0, maxActiveDepth - depth)
    const spacing = calculateDynamicSpacing(distanceFromLatest)
    depthSpacingMap.set(depth, spacing)
  }

  // Calculate cumulative X positions for ALL depths (not just active branch)
  const depthToXMap = new Map<number, number>()
  let cumulativeX = LEFT_MARGIN
  depthToXMap.set(0, cumulativeX)
  for (let depth = 0; depth < maxDepth; depth++) {
    const spacing = depthSpacingMap.get(depth)
    if (spacing === undefined) {
      throw new Error(`Spacing not found for depth ${depth}`)
    }
    cumulativeX += spacing
    depthToXMap.set(depth + 1, cumulativeX)
  }

  // Assign X,Y positions to all nodes
  const positionedNodes: PositionedNode[] = []

  function assignPositions(node: D3TreeNode, depth: number): void {
    let x = depthToXMap.get(depth)
    if (x === undefined) {
      // Fallback: calculate position for unexpected depths
      const lastDepth = Math.max(...Array.from(depthToXMap.keys()))
      const lastX = depthToXMap.get(lastDepth) || LEFT_MARGIN
      // Use default spacing for depths beyond what we calculated
      const defaultSpacing = calculateDynamicSpacing(0)
      x = lastX + (depth - lastDepth) * defaultSpacing
      depthToXMap.set(depth, x)
    }
    const y = agentYMap.get(node.data.agent_name)
    if (y === undefined) {
      throw new Error(`Agent ${node.data.agent_name} not found in swimlane map`)
    }

    // Store position on node for D3
    node.x = x
    node.y = y

    positionedNodes.push({ node, x, y })

    // Recursively process children
    if (node.children) {
      node.children.forEach(child => {
        assignPositions(child as D3TreeNode, depth + 1)
      })
    }
  }

  assignPositions(root, 0)

  // Collect all edges
  const edges: Edge[] = []
  const nodeMap = new Map<string, PositionedNode>()
  positionedNodes.forEach(pNode => {
    nodeMap.set(pNode.node.data.id, pNode)
  })

  positionedNodes.forEach(pNode => {
    if (pNode.node.children) {
      pNode.node.children.forEach(child => {
        const childPositioned = nodeMap.get((child as D3TreeNode).data.id)

        if (!childPositioned) {
          throw new Error(`Child node ${(child as D3TreeNode).data.id} not found`)
        }

        edges.push({
          source: pNode,
          target: childPositioned,
          sourceX: pNode.x,
          sourceY: pNode.y,
          targetX: childPositioned.x,
          targetY: childPositioned.y,
        })
      })
    }
  })

  // ============================================================
  // PHASE 2: RENDER SWIMLANE INFRASTRUCTURE
  // ============================================================

  // Render alternating background rectangles
  const swimlanes = g
    .selectAll<SVGRectElement, string>('.swimlane-bg')
    .data(swimlaneNames, (d: string) => d)

  const swimlanesEnter = swimlanes
    .enter()
    .insert('rect', ':first-child')
    .attr('class', 'swimlane-bg')

  swimlanesEnter
    .merge(swimlanes)
    .attr('x', 0)
    .attr('y', (d: string) => {
      const centerY = swimlaneYMap.get(d)
      if (centerY === undefined) {
        throw new Error(`Swimlane ${d} not found in map`)
      }
      return centerY - (SWIMLANE_HEIGHT / 2)
    })
    .attr('width', 10000)
    .attr('height', SWIMLANE_HEIGHT)
    .attr('fill', (_d: string, i: number) => {
      return i % 2 === 0 ? '#1c1f26' : '#21242b'
    })
    .attr('opacity', 0.6)

  swimlanes.exit().remove()

  // Render agent name labels on left
  const labels = g
    .selectAll<SVGTextElement, string>('.swimlane-label')
    .data(swimlaneNames, (d: string) => d)

  const labelsEnter = labels
    .enter()
    .append('text')
    .attr('class', 'swimlane-label')

  labelsEnter
    .merge(labels)
    .attr('x', 10)
    .attr('y', (d: string) => {
      const centerY = swimlaneYMap.get(d)
      if (centerY === undefined) {
        throw new Error(`Swimlane ${d} not found in map`)
      }
      return centerY
    })
    .attr('dy', '0.35em')
    .attr('text-anchor', 'start')
    .text((d: string) => {
      const displayName = swimlaneDisplayNames.get(d)
      if (displayName === undefined) {
        throw new Error(`Display name for swimlane ${d} not found`)
      }
      return displayName
    })
    .style('fill', '#8b949e')
    .style('font-size', '13px')
    .style('font-weight', '600')
    .style('font-family', 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif')
    .style('pointer-events', 'none')

  labels.exit().remove()

  // ============================================================
  // PHASE 3: RENDER EDGES
  // ============================================================

  // Create horizontal Bezier curve path for edges
  function createHorizontalPath(d: Edge): string {
    const midX = (d.sourceX + d.targetX) / 2
    return `M ${d.sourceX},${d.sourceY} C ${midX},${d.sourceY} ${midX},${d.targetY} ${d.targetX},${d.targetY}`
  }

  const link = g
    .selectAll<SVGPathElement, Edge>('.link')
    .data(edges, (d: Edge) => `${d.source.node.data.id}-${d.target.node.data.id}`)

  link.exit().remove()

  const linkEnter = link
    .enter()
    .append('path')
    .attr('class', 'link')

  linkEnter
    .merge(link)
    .attr('d', createHorizontalPath)
    .attr('fill', 'none')
    .attr('stroke', (d: Edge) => {
      if (edgeInterrupt && edgeInterrupt.targetNodeId === d.target.node.data.id) {
        return '#ef4444'
      }
      return d.target.node.data.is_active ? '#58a6ff' : '#30363d'
    })
    .attr('stroke-width', (d: Edge) => {
      if (edgeInterrupt && edgeInterrupt.targetNodeId === d.target.node.data.id) {
        return 4
      }
      return d.target.node.data.is_active ? 2 : 1
    })
    .attr('opacity', (d: Edge) => d.target.node.data.is_active ? 1 : 0.3)
    .style('cursor', (d: Edge) => d.target.node.data.is_active ? 'pointer' : 'default')
    .on('mouseenter', function (this: SVGPathElement, _event: MouseEvent, d: Edge) {
      if (d.target.node.data.is_active) {
        d3.select(this)
          .transition()
          .duration(150)
          .attr('stroke-width', Number(d3.select(this).attr('stroke-width')) + 2)
      }
    })
    .on('mouseleave', function (this: SVGPathElement, _event: MouseEvent, d: Edge) {
      const baseWidth = d.target.node.data.is_active ? 2 : 1
      const interrupted = edgeInterrupt && edgeInterrupt.targetNodeId === d.target.node.data.id
      d3.select(this)
        .transition()
        .duration(200)
        .attr('stroke-width', interrupted ? 4 : baseWidth)
    })
    .on('click', function (event: MouseEvent, d: Edge) {
      if (onEdgeClick && d.target.node.data.is_active && treeData) {
        event.stopPropagation()
        const trimCount = calculateTrimCount(d.target.node.data.id, treeData)
        onEdgeClick(d.target.node.data.id, { x: event.clientX, y: event.clientY }, trimCount)
      }
    })

  // ============================================================
  // PHASE 4: RENDER NODES
  // ============================================================

  const nodes = g
    .selectAll<SVGGElement, PositionedNode>('.node')
    .data(positionedNodes, (d: PositionedNode) => d.node.data.id)

  nodes.exit().remove()

  const nodeEnter = nodes
    .enter()
    .append('g')
    .attr('class', 'node')

  nodeEnter
    .append('circle')
    .attr('class', 'node-circle')
    .attr('r', NODE_RADIUS)
    .attr('fill', (d: PositionedNode) => {
      const node = d.node.data
      if (node.node_type === 'tool_call' || node.node_type === 'tool_execution') {
        return '#1f6feb'
      }
      return node.is_active ? '#238636' : '#30363d'
    })
    .attr('stroke', (d: PositionedNode) => {
      // Yellow border for triggered nodes
      if (triggeredNodes.has(d.node.data.id)) {
        return '#fbbf24'
      }
      return '#58a6ff'
    })
    .attr('stroke-width', (d: PositionedNode) => {
      // Thicker border for triggered nodes
      return triggeredNodes.has(d.node.data.id) ? 3 : 2
    })

  const nodeUpdate = nodeEnter.merge(nodes)

  nodeUpdate
    .transition()
    .duration(ANIMATION_DURATION)
    .attr('transform', (d: PositionedNode) => `translate(${d.x},${d.y})`)
    .attr('opacity', (d: PositionedNode) => d.node.data.is_active ? 1 : 0.4)
    .style('cursor', 'pointer')

  nodeUpdate.selectAll<SVGCircleElement, PositionedNode>('.node-circle')
    .attr('fill', (d: PositionedNode) => {
      const node = d.node.data
      if (node.node_type === 'tool_call' || node.node_type === 'tool_execution') {
        return '#1f6feb'
      }
      return node.is_active ? '#238636' : '#30363d'
    })
    .attr('stroke', (d: PositionedNode) => {
      // Yellow border for triggered nodes
      if (triggeredNodes.has(d.node.data.id)) {
        return '#fbbf24'
      }
      return '#58a6ff'
    })
    .attr('stroke-width', (d: PositionedNode) => {
      // Thicker border for triggered nodes
      return triggeredNodes.has(d.node.data.id) ? 3 : 2
    })

  nodeUpdate
    .on('click', function (event: MouseEvent, d: PositionedNode) {
      event.stopPropagation()
      if (onNodeClick) {
        onNodeClick(d.node.data.id, getConversationItemTypeForNode(d.node.data))
      }
    })

  // ============================================================
  // PHASE 5: RENDER ANALYSIS BADGES
  // ============================================================

  // Remove existing badges first
  nodeUpdate.selectAll('.node-analysis-badges').remove()

  let badgesRendered = 0

  // Add analysis badges to nodes that have scores
  nodeUpdate.each(function (this: SVGGElement, d: PositionedNode) {
    const nodeScores = analysisScores.get(d.node.data.id)

    if (nodeScores) {
      badgesRendered++
      console.log(`   ✓ Rendering badges for node ${d.node.data.id}`)

      const nodeGroup = d3.select<SVGGElement, PositionedNode>(this)

      // Create a group for analysis bars positioned below the node
      const barGroup = nodeGroup
        .append('g')
        .attr('class', 'node-analysis-badges')
        .attr('transform', `translate(${-NODE_RADIUS}, ${NODE_RADIUS + 8})`)

      const barHeight = 4
      const barSpacing = 2
      const maxBarWidth = NODE_RADIUS * 2 // Match node width

      // Render horizontal bars for each component
      analysisComponents.forEach((component, index) => {
        const score = nodeScores.scores[component.label]?.score || 0
        const barWidth = (score / 10) * maxBarWidth // Scale 0-10 to bar width

        // Background bar (light gray)
        barGroup
          .append('rect')
          .attr('x', 0)
          .attr('y', index * (barHeight + barSpacing))
          .attr('width', maxBarWidth)
          .attr('height', barHeight)
          .attr('fill', '#2a2a2a')
          .attr('rx', 1)

        // Foreground bar (colored by score)
        barGroup
          .append('rect')
          .attr('x', 0)
          .attr('y', index * (barHeight + barSpacing))
          .attr('width', barWidth)
          .attr('height', barHeight)
          .attr('fill', component.color)
          .attr('opacity', 0.8)
          .attr('rx', 1)
          .style('cursor', 'pointer')
          .append('title')
          .text(`${component.label}: ${score}/10\n${nodeScores.scores[component.label]?.reasoning || ''}`)
      })
    }
  })

  // Add triggered node indicator (warning icon)
  nodeUpdate.selectAll('.node-triggered-indicator').remove()

  nodeUpdate.each(function (this: SVGGElement, d: PositionedNode) {
    if (triggeredNodes.has(d.node.data.id)) {
      const nodeGroup = d3.select<SVGGElement, PositionedNode>(this)

      // Add a small warning circle indicator
      const indicatorGroup = nodeGroup
        .append('g')
        .attr('class', 'node-triggered-indicator')
        .attr('transform', `translate(${NODE_RADIUS - 2}, ${-NODE_RADIUS + 2})`)

      // Background circle
      indicatorGroup
        .append('circle')
        .attr('r', 6)
        .attr('fill', '#fbbf24')
        .attr('stroke', '#0d1117')
        .attr('stroke-width', 1.5)

      // Warning symbol (exclamation mark) using text
      indicatorGroup
        .append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '0.35em')
        .attr('font-size', '10px')
        .attr('font-weight', 'bold')
        .attr('fill', '#0d1117')
        .text('!')
        .append('title')
        .text('Analysis triggered feedback')
    }
  })
}
