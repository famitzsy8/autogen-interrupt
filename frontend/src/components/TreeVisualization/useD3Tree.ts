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
import { getColorForScore, assignSequentialScheme, type SequentialSchemeName, getAgentColorD3, registerAgentColors } from '../../utils/colorSchemes'

// Helper to get CSS variable values for theme-aware D3 rendering
function getCssVar(varName: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim()
}

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
  userInterruptedNodes?: Set<string>
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
const LEFT_MARGIN = 150              // Left margin before first nodes
const NODE_RADIUS = 13               // Radius of node circles (60% larger than original 8)

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
    userInterruptedNodes = new Set(),
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
  const [hoveredSummaryNodeIds, setHoveredSummaryNodeIds] = useState<Set<string>>(new Set())
  const [foregroundSummaryId, setForegroundSummaryId] = useState<string | null>(null)
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
      .filter((event: Event) => {
        // Allow wheel events for zooming
        if (event.type === 'wheel') return true
        // Allow double-click zoom
        if (event.type === 'dblclick') return true
        // For mouse/touch events, check if target is an interactive element
        if (event.type === 'mousedown' || event.type === 'touchstart') {
          const target = event.target as Element
          // Don't initiate pan/drag if clicking on interactive elements (circles, nodes, edges)
          if (target.classList.contains('summary-circle') ||
              target.classList.contains('node-circle') ||
              target.classList.contains('edge-path') ||
              target.closest('.summary-circle') ||
              target.closest('.node-group') ||
              target.closest('.edge-group')) {
            return false
          }
          return true // Allow drag on empty space
        }
        return false
      })
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

    // Note: Agent colors are registered later in renderTree() after swimlanes are sorted
    // This ensures colors progress from light (top) to dark (bottom) matching vertical position

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
      userInterruptedNodes,
      hoveredSummaryNodeIds,
      onSummaryHover: (nodeId: string | null) => {
        if (nodeId) {
          setHoveredSummaryNodeIds(prev => new Set([...prev, nodeId]))
        }
      },
      onSummaryHoverOut: (nodeId: string | null) => {
        if (nodeId) {
          setHoveredSummaryNodeIds(prev => {
            const newSet = new Set(prev)
            newSet.delete(nodeId)
            return newSet
          })
        }
      },
      foregroundSummaryId,
      onSummaryForeground: (nodeId: string | null) => {
        setForegroundSummaryId(nodeId)
      },
    })

    // After tree updates, preserve transform in navigation mode
    if (!autoCenterEnabled && svgRef.current && zoomRef.current) {
      const svg = d3.select(svgRef.current)
      // Use a very short timeout to let D3 finish its update first
      setTimeout(() => {
        svg.call(zoomRef.current!.transform, transformRef.current)
      }, 0)
    }
  }, [root, activeNodeIds, width, height, treeConfig, toolCallsByNodeId, toolExecutionsByNodeId, edgeInterrupt, onEdgeClick, autoCenterEnabled, onNodeClick, analysisComponents, analysisScores, triggeredNodes, userInterruptedNodes, hoveredSummaryNodeIds, foregroundSummaryId])

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
  userInterruptedNodes: Set<string>
  hoveredSummaryNodeIds: Set<string>
  onSummaryHover: (nodeId: string | null) => void
  onSummaryHoverOut: (nodeId: string | null) => void
  foregroundSummaryId: string | null
  onSummaryForeground: (nodeId: string | null) => void
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
    userInterruptedNodes,
    hoveredSummaryNodeIds,
    onSummaryHover,
    onSummaryHoverOut,
    foregroundSummaryId,
    onSummaryForeground,
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

  // Register agent colors in sorted swimlane order
  // This ensures colors progress from light (top) to dark (bottom) matching vertical position
  registerAgentColors(swimlaneNames)

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
  // LAYER SETUP: Create layer groups for proper z-ordering
  // SVG renders elements in document order, so later groups appear on top
  // ============================================================

  // Ensure layer groups exist (create them in order: bottom to top)
  // Check if layers already exist to avoid duplicating on updates
  let swimlaneLayer = g.select<SVGGElement>('.layer-swimlanes')
  if (swimlaneLayer.empty()) {
    swimlaneLayer = g.append('g').attr('class', 'layer-swimlanes')
  }

  let edgesLayer = g.select<SVGGElement>('.layer-edges')
  if (edgesLayer.empty()) {
    edgesLayer = g.append('g').attr('class', 'layer-edges')
  }

  let nodesLayer = g.select<SVGGElement>('.layer-nodes')
  if (nodesLayer.empty()) {
    nodesLayer = g.append('g').attr('class', 'layer-nodes')
  }

  let summariesLayer = g.select<SVGGElement>('.layer-summaries')
  if (summariesLayer.empty()) {
    summariesLayer = g.append('g').attr('class', 'layer-summaries')
  }

  // ============================================================
  // PHASE 2: RENDER SWIMLANE INFRASTRUCTURE
  // ============================================================

  // Render alternating background rectangles
  const swimlanes = swimlaneLayer
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
    .attr('rx', 8)
    .attr('ry', 8)
    .attr('fill', (d: string) => {
      // Use theme-aware colors for swimlanes
      if (d === 'User') {
        return getCssVar('--color-surface-elevated')
      }
      return getCssVar('--color-surface')
    })
    .attr('opacity', (d: string) => {
      // Higher opacity for User lane to make it stand out
      return d === 'User' ? 1 : 0.8
    })
    .attr('stroke', () => {
      return getCssVar('--color-border')
    })
    .attr('stroke-width', (d: string) => {
      return d === 'User' ? 1 : 0
    })

  swimlanes.exit().remove()

  // Render agent name labels on left with colored boxes
  const labelGroups = swimlaneLayer
    .selectAll<SVGGElement, string>('.swimlane-label-group')
    .data(swimlaneNames, (d: string) => d)

  const labelGroupsEnter = labelGroups
    .enter()
    .append('g')
    .attr('class', 'swimlane-label-group')

  // Add colored background rectangle to each label
  labelGroupsEnter
    .append('rect')
    .attr('class', 'swimlane-label-bg')

  // Add text to each label
  labelGroupsEnter
    .append('text')
    .attr('class', 'swimlane-label-text')

  const labelGroupsMerged = labelGroupsEnter.merge(labelGroups)

  // Update group position
  labelGroupsMerged
    .attr('transform', (d: string) => {
      const centerY = swimlaneYMap.get(d)
      if (centerY === undefined) {
        throw new Error(`Swimlane ${d} not found in map`)
      }
      return `translate(10, ${centerY})`
    })

  // Update text labels FIRST (so we can measure their width)
  labelGroupsMerged.selectAll<SVGTextElement, string>('.swimlane-label-text')
    .data((d: string) => [d])
    .attr('x', 6)
    .attr('y', 0)
    .attr('dy', '0.05em')
    .attr('text-anchor', 'start')
    .attr('dominant-baseline', 'middle')
    .text((d: string) => {
      const displayName = swimlaneDisplayNames.get(d)
      if (displayName === undefined) {
        throw new Error(`Display name for swimlane ${d} not found`)
      }
      return displayName
    })
    .style('fill', '#ffffff') // Always white on colored agent badge
    .style('font-size', '20px')
    .style('font-weight', '600')
    .style('line-height', '1')
    .style('font-family', 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif')
    .style('pointer-events', 'none')

  // Update background rectangles with agent colors (measure actual text width)
  labelGroupsMerged.each(function (this: SVGGElement, d: string) {
    const group = d3.select<SVGGElement, string>(this)
    const textElement = group.select<SVGTextElement>('.swimlane-label-text').node()

    if (!textElement) {
      throw new Error(`Text element not found for swimlane ${d}`)
    }

    // Measure actual text width
    const textBBox = textElement.getBBox()
    const padding = 16 // 8px padding on each side
    const actualWidth = textBBox.width + padding

    // Get agent color
    let agentNameForColor = d
    rawAgentNames.forEach(name => {
      const normalized = normalizeAgentName(name)
      if (normalized === d) {
        agentNameForColor = name
      }
    })

    group.select<SVGRectElement>('.swimlane-label-bg')
      .attr('x', 0)
      .attr('y', -14)
      .attr('width', actualWidth)
      .attr('height', 28)
      .attr('rx', 14)
      .attr('fill', getAgentColorD3(agentNameForColor))
      .attr('opacity', 0.9)
      .style('pointer-events', 'none')
  })

  labelGroups.exit().remove()

  // ============================================================
  // PHASE 3: RENDER EDGES
  // ============================================================

  // Create horizontal Bezier curve path for edges
  function createHorizontalPath(d: Edge): string {
    const midX = (d.sourceX + d.targetX) / 2
    return `M ${d.sourceX},${d.sourceY} C ${midX},${d.sourceY} ${midX},${d.targetY} ${d.targetX},${d.targetY}`
  }

  const link = edgesLayer
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
      // Use theme-aware edge color
      return getCssVar('--color-edge')
    })
    .attr('stroke-width', (d: Edge) => {
      if (edgeInterrupt && edgeInterrupt.targetNodeId === d.target.node.data.id) {
        return 8
      }
      return d.target.node.data.is_active ? 5 : 3
    })
    .attr('opacity', (d: Edge) => d.target.node.data.is_active ? 1 : 0.2)
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
      const baseWidth = d.target.node.data.is_active ? 5 : 3
      const interrupted = edgeInterrupt && edgeInterrupt.targetNodeId === d.target.node.data.id
      d3.select(this)
        .transition()
        .duration(200)
        .attr('stroke-width', interrupted ? 8 : baseWidth)
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

  const nodes = nodesLayer
    .selectAll<SVGGElement, PositionedNode>('.node')
    .data(positionedNodes, (d: PositionedNode) => d.node.data.id)

  nodes.exit().remove()

  const nodeEnter = nodes
    .enter()
    .append('g')
    .attr('class', 'node')

  // Append circles for non-tool nodes
  nodeEnter
    .filter((d: PositionedNode) => d.node.data.node_type !== 'tool_call' && d.node.data.node_type !== 'tool_execution')
    .append('circle')
    .attr('class', 'node-shape')
    .attr('r', NODE_RADIUS)
    .attr('fill', (d: PositionedNode) => getAgentColorD3(d.node.data.agent_name))
    .attr('fill-opacity', 0.9)

  // Append squares (rect) for tool_call and tool_execution nodes
  const squareSize = NODE_RADIUS * 1.6
  nodeEnter
    .filter((d: PositionedNode) => d.node.data.node_type === 'tool_call' || d.node.data.node_type === 'tool_execution')
    .append('rect')
    .attr('class', 'node-shape')
    .attr('x', -squareSize / 2)
    .attr('y', -squareSize / 2)
    .attr('width', squareSize)
    .attr('height', squareSize)
    .attr('rx', 2) // Slight corner rounding
    .attr('fill', (d: PositionedNode) => getAgentColorD3(d.node.data.agent_name))
    .attr('fill-opacity', 0.5)

  const nodeUpdate = nodeEnter.merge(nodes)

  nodeUpdate
    .transition()
    .duration(ANIMATION_DURATION)
    .attr('transform', (d: PositionedNode) => `translate(${d.x},${d.y})`)
    .attr('opacity', (d: PositionedNode) => d.node.data.is_active ? 1 : 0.25)
    .style('cursor', 'pointer')

  nodeUpdate.selectAll<SVGElement, PositionedNode>('.node-shape')
    .attr('fill', (d: PositionedNode) => getAgentColorD3(d.node.data.agent_name))
    .attr('fill-opacity', (d: PositionedNode) => {
      // Tool calls have lower opacity (0.5), messages have higher opacity (0.9)
      if (d.node.data.node_type === 'tool_call' || d.node.data.node_type === 'tool_execution') {
        return 0.5
      }
      return 0.9
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

      const nodeGroup = d3.select<SVGGElement, PositionedNode>(this)

      // Create a group for analysis bars positioned below the node
      const barGroup = nodeGroup
        .append('g')
        .attr('class', 'node-analysis-badges')
        .attr('transform', `translate(${-NODE_RADIUS}, ${NODE_RADIUS + 8})`)

      const barHeight = 12
      const maxBarWidth = NODE_RADIUS * 2 * 3 // 3x wider to match 3x height increase

      // Find the maximum score across all components
      let maxScore = 0
      let maxScoreComponentLabel = ''
      let maxScoreComponentScheme: string | undefined = undefined
      let maxScoreIndex = 0
      analysisComponents.forEach((component, index) => {
        const score = nodeScores.scores[component.label]?.score || 0
        if (score > maxScore) {
          maxScore = score
          maxScoreComponentLabel = component.label
          maxScoreComponentScheme = component.sequentialScheme
          maxScoreIndex = index
        }
      })

      // Render a single aggregated bar with the max value
      const barWidth = (maxScore / 10) * maxBarWidth // Scale 0-10 to bar width

      // Determine sequential scheme for the max-scoring component
      let schemeName: SequentialSchemeName = 'OrRd'
      if (maxScoreComponentLabel) {
        if (maxScoreComponentScheme) {
          schemeName = maxScoreComponentScheme as SequentialSchemeName
        } else {
          schemeName = assignSequentialScheme(maxScoreComponentLabel, maxScoreIndex)
        }
      }

      // Get color based on the actual max score value
      const barColor = getColorForScore(schemeName, maxScore)

      // Background bar (lighter gray with border for better visibility)
      barGroup
        .append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', maxBarWidth)
        .attr('height', barHeight)
        .attr('fill', getCssVar('--color-surface'))
        .attr('stroke', getCssVar('--color-border'))
        .attr('stroke-width', 1)
        .attr('rx', 6)
        .attr('ry', 6)

      // Foreground bar (colored by max score)
      const foregroundBar = barGroup
        .append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', barWidth)
        .attr('height', barHeight)
        .attr('fill', barColor)
        .attr('opacity', 0.9)
        .attr('rx', 6)
        .attr('ry', 6)
        .style('cursor', 'pointer')

      // Build tooltip with all component scores
      const tooltipLines = analysisComponents.map(component => {
        const score = nodeScores.scores[component.label]?.score || 0
        return `${component.label}: ${score}/10`
      })
      foregroundBar
        .append('title')
        .text(`Max: ${maxScore}/10\n${tooltipLines.join('\n')}`)
    }
  })

  // Add triggered node indicator (warning icon)
  nodeUpdate.selectAll('.node-triggered-indicator').remove()

  nodeUpdate.each(function (this: SVGGElement, d: PositionedNode) {
    if (triggeredNodes.has(d.node.data.id)) {
      const nodeGroup = d3.select<SVGGElement, PositionedNode>(this)

      // Add a larger warning indicator positioned above the node
      const indicatorGroup = nodeGroup
        .append('g')
        .attr('class', 'node-triggered-indicator')
        .attr('transform', `translate(0, ${-NODE_RADIUS - 20})`)

      // Background circle
      indicatorGroup
        .append('circle')
        .attr('r', 16)
        .attr('fill', '#fbbf24') // Yellow warning color - intentionally fixed
        .attr('stroke', getCssVar('--color-bg'))
        .attr('stroke-width', 2)

      // Warning symbol (exclamation mark) using text
      indicatorGroup
        .append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '0.35em')
        .attr('font-size', '22px')
        .attr('font-weight', 'bold')
        .attr('fill', getCssVar('--color-bg'))
        .text('!')
        .append('title')
        .text('Analysis triggered feedback')
    }
  })

  // Add user-interrupted node indicator (red exclamation mark)
  nodeUpdate.selectAll('.node-user-interrupted-indicator').remove()

  nodeUpdate.each(function (this: SVGGElement, d: PositionedNode) {
    if (userInterruptedNodes.has(d.node.data.id)) {
      const nodeGroup = d3.select<SVGGElement, PositionedNode>(this)

      // Check if this node already has a triggered indicator to offset position
      const hasTriggeredIndicator = triggeredNodes.has(d.node.data.id)
      const xOffset = hasTriggeredIndicator ? 24 : 0 // Offset to the right if triggered indicator exists

      // Add a red indicator positioned above the node
      const indicatorGroup = nodeGroup
        .append('g')
        .attr('class', 'node-user-interrupted-indicator')
        .attr('transform', `translate(${xOffset}, ${-NODE_RADIUS - 20})`)

      // Background circle (red)
      indicatorGroup
        .append('circle')
        .attr('r', 16)
        .attr('fill', '#ef4444') // Red triggered color - intentionally fixed
        .attr('stroke', getCssVar('--color-bg'))
        .attr('stroke-width', 2)

      // Exclamation mark symbol
      indicatorGroup
        .append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '0.35em')
        .attr('font-size', '22px')
        .attr('font-weight', 'bold')
        .attr('fill', getCssVar('--color-text'))
        .text('!')
        .append('title')
        .text('User interrupted at this point')
    }
  })

  // ============================================================
  // PHASE 6: RENDER NODE SUMMARIES BELOW SWIMLANES
  // ============================================================

  // Calculate the Y position for the summary area (below all swimlanes)
  const totalTreeHeight = swimlaneNames.length * SWIMLANE_HEIGHT
  const summaryAreaY = totalTreeHeight + 40 // 40px gap below last swimlane
  // Circle dimensions for hoverable indicators (only for older summaries, not last 3)
  const circleRadius = 14
  const circleY = summaryAreaY // Y position for circles (above summaries)
  const expandedSummaryY = summaryAreaY + 40 // Y position for expanded summaries (below circles)

  // Add "Summaries" label on the left side (same position as agent name labels)
  summariesLayer.selectAll('.summaries-label-group').remove()
  const summariesLabelGroup = summariesLayer
    .append('g')
    .attr('class', 'summaries-label-group')
    .attr('transform', `translate(10, ${circleY})`)

  // Add colored background rectangle
  const summariesLabelText = summariesLabelGroup
    .append('text')
    .attr('class', 'summaries-label-text')
    .attr('x', 6)
    .attr('y', 0)
    .attr('dy', '0.05em')
    .attr('text-anchor', 'start')
    .attr('dominant-baseline', 'middle')
    .text('Summaries')
    .style('fill', '#ffffff')
    .style('font-size', '16px')
    .style('font-weight', '600')
    .style('font-family', 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif')
    .style('pointer-events', 'none')

  // Measure text and add background
  const textNode = summariesLabelText.node()
  if (textNode) {
    const textBBox = textNode.getBBox()
    const padding = 12
    const actualWidth = textBBox.width + padding

    // Insert background rect before text
    summariesLabelGroup
      .insert('rect', 'text')
      .attr('class', 'summaries-label-bg')
      .attr('x', 0)
      .attr('y', -12)
      .attr('width', actualWidth)
      .attr('height', 24)
      .attr('rx', 12)
      .attr('fill', getCssVar('--color-text-secondary')) // Theme-aware gray for summaries
      .attr('opacity', 0.9)
      .style('pointer-events', 'none')
  }

  // Helper function to calculate dynamic box dimensions based on text length
  const calculateBoxDimensions = (text: string): { width: number; height: number } => {
    const minWidth = 200
    const maxWidth = 500
    const minHeight = 50
    const maxHeight = 120
    const avgCharWidth = 7 // approximate pixel width per character
    const charsPerLine = 50 // target characters per line

    // Estimate width based on text length
    const estimatedWidth = Math.min(maxWidth, Math.max(minWidth, text.length * avgCharWidth / 2))

    // Estimate height based on number of lines needed
    const estimatedLines = Math.ceil(text.length / charsPerLine)
    const estimatedHeight = Math.min(maxHeight, Math.max(minHeight, estimatedLines * 20 + 20)) // 20px per line + padding

    return { width: estimatedWidth, height: estimatedHeight }
  }

  // Remove existing summary elements
  summariesLayer.selectAll('.node-summary-group').remove()

  // Filter nodes that have summaries and are in the active branch
  const nodesWithSummaries = positionedNodes.filter(
    pNode => pNode.node.data.summary && pNode.node.data.summary.trim() !== '' && pNode.node.data.is_active
  )

  // Sort by depth (position in active path) to find the last 3
  const sortedNodesWithSummaries = [...nodesWithSummaries].sort((a, b) => b.node.depth - a.node.depth)

  // Get the last 3 node IDs that should be always displayed (no hover needed)
  const last3SummaryNodeIds = new Set(
    sortedNodesWithSummaries.slice(0, 3).map(pNode => pNode.node.data.id)
  )

  // Get ALL visible summaries: last 3 + any toggled ones, sorted by depth (oldest first)
  const visibleSummaries = nodesWithSummaries
    .filter(pNode => last3SummaryNodeIds.has(pNode.node.data.id) || hoveredSummaryNodeIds.has(pNode.node.data.id))
    .sort((a, b) => a.node.depth - b.node.depth) // Sort oldest first (lowest depth)

  // Calculate y-offsets to fully separate overlapping summaries
  // Each summary checks against all previously placed summaries and stacks below if overlapping
  interface OverlapInfo {
    yOffset: number       // Y offset to avoid overlap
    boxHeight: number     // Height of this summary box
  }
  const overlapMap = new Map<string, OverlapInfo>()
  const VERTICAL_GAP = 10 // Gap between stacked summaries

  // Track placed summaries with their bounds
  interface PlacedSummary {
    id: string
    left: number
    right: number
    yOffset: number
    height: number
  }
  const placedSummaries: PlacedSummary[] = []

  // Process summaries from oldest to newest (so newer ones stack on top/below older ones)
  for (const current of visibleSummaries) {
    const currentBox = calculateBoxDimensions(current.node.data.summary)
    const currentLeft = current.x - currentBox.width / 2
    const currentRight = current.x + currentBox.width / 2

    // Find all summaries this one overlaps with horizontally
    const overlappingPlacements = placedSummaries.filter(placed => {
      return !(currentRight < placed.left || currentLeft > placed.right)
    })

    // Calculate y-offset: stack below all overlapping summaries
    let yOffset = 0
    if (overlappingPlacements.length > 0) {
      // Find the bottom of the lowest overlapping summary
      const maxBottom = Math.max(...overlappingPlacements.map(p => p.yOffset + p.height))
      yOffset = maxBottom + VERTICAL_GAP
    }

    // If this summary is being hovered, bring it to front (y=0) and push others down
    if (foregroundSummaryId === current.node.data.id) {
      yOffset = 0
    }

    overlapMap.set(current.node.data.id, { yOffset, boxHeight: currentBox.height })

    // Add to placed summaries
    placedSummaries.push({
      id: current.node.data.id,
      left: currentLeft,
      right: currentRight,
      yOffset,
      height: currentBox.height
    })
  }

  // If a summary is hovered, recalculate offsets to push overlapping ones down
  if (foregroundSummaryId) {
    const hoveredSummary = visibleSummaries.find(s => s.node.data.id === foregroundSummaryId)
    if (hoveredSummary) {
      const hoveredBox = calculateBoxDimensions(hoveredSummary.node.data.summary)
      const hoveredLeft = hoveredSummary.x - hoveredBox.width / 2
      const hoveredRight = hoveredSummary.x + hoveredBox.width / 2

      // Hovered summary is at y=0
      overlapMap.set(foregroundSummaryId, { yOffset: 0, boxHeight: hoveredBox.height })

      // Recalculate positions for non-hovered summaries
      let currentYOffset = hoveredBox.height + VERTICAL_GAP

      for (const summary of visibleSummaries) {
        if (summary.node.data.id === foregroundSummaryId) continue

        const box = calculateBoxDimensions(summary.node.data.summary)
        const left = summary.x - box.width / 2
        const right = summary.x + box.width / 2

        // Check if this overlaps horizontally with hovered
        const overlapsWithHovered = !(right < hoveredLeft || left > hoveredRight)

        if (overlapsWithHovered) {
          overlapMap.set(summary.node.data.id, { yOffset: currentYOffset, boxHeight: box.height })
          currentYOffset += box.height + VERTICAL_GAP
        }
        // Non-overlapping summaries keep their original offset (already in overlapMap)
      }
    }
  }

  // Create summary groups for each node with a summary
  const summaryGroups = summariesLayer
    .selectAll<SVGGElement, PositionedNode>('.node-summary-group')
    .data(nodesWithSummaries, (d: PositionedNode) => d.node.data.id)

  summaryGroups.exit().remove()

  const summaryGroupsEnter = summaryGroups
    .enter()
    .append('g')
    .attr('class', 'node-summary-group')

  const summaryGroupsMerged = summaryGroupsEnter.merge(summaryGroups)

  // Position summary groups at node X position (circles are always at circleY)
  summaryGroupsMerged
    .attr('transform', (d: PositionedNode) => {
      // Position group at node's X, with circle at circleY
      return `translate(${d.x}, ${circleY})`
    })

  // Add circle indicators only for OLDER summaries (not the last 3 which are always visible)
  summaryGroupsMerged.selectAll('.summary-circle').remove()

  // Filter to only show circles for nodes NOT in last 3
  const olderSummaryGroups = summaryGroupsMerged
    .filter((d: PositionedNode) => !last3SummaryNodeIds.has(d.node.data.id))

  olderSummaryGroups
    .append('circle')
    .attr('class', 'summary-circle')
    .attr('cx', 0)
    .attr('cy', 0)
    .attr('r', circleRadius)
    .attr('fill', (d: PositionedNode) => {
      // Grey when not toggled, slightly lighter when toggled
      const isToggled = hoveredSummaryNodeIds.has(d.node.data.id)
      return isToggled ? getCssVar('--color-text-muted') : getCssVar('--color-text-faint')
    })
    .attr('stroke', (d: PositionedNode) => {
      const isToggled = hoveredSummaryNodeIds.has(d.node.data.id)
      return isToggled ? getCssVar('--color-text-secondary') : getCssVar('--color-text-muted')
    })
    .attr('stroke-width', 2)
    .attr('opacity', 0.9)
    .style('pointer-events', 'all')
    .style('cursor', 'pointer')
    .on('click', function (event: MouseEvent, d: PositionedNode) {
      // Stop propagation to prevent other handlers from interfering
      event.stopPropagation()

      const isToggled = hoveredSummaryNodeIds.has(d.node.data.id)

      // Toggle: if already showing, hide it; if hidden, show it
      if (isToggled) {
        onSummaryHoverOut(d.node.data.id)
      } else {
        onSummaryHover(d.node.data.id)
      }
    })

  // Offset from circle center to expanded summary box (positioned below circles)
  const summaryOffsetY = expandedSummaryY - circleY

  // Add summary box background (only when expanded) - positioned below circles
  summaryGroupsMerged.selectAll('.summary-box-bg').remove()
  summaryGroupsMerged.selectAll('.summary-expanded-group').remove()

  // Show summary for: last 3 (always visible) OR currently toggled (for older summaries)
  const expandedBoxes = summaryGroupsMerged
    .filter((d: PositionedNode) => last3SummaryNodeIds.has(d.node.data.id) || hoveredSummaryNodeIds.has(d.node.data.id))

  // Create a sub-group for expanded summaries positioned below the circles
  // Apply y-offset based on overlap detection (works for both last 3 and toggled summaries)
  const expandedGroups = expandedBoxes
    .append('g')
    .attr('class', 'summary-expanded-group')
    .attr('transform', (d: PositionedNode) => {
      const boxDimensions = calculateBoxDimensions(d.node.data.summary)
      // Get overlap offset from the map (applies to all visible summaries)
      const overlapInfo = overlapMap.get(d.node.data.id)
      const yOffset = overlapInfo ? overlapInfo.yOffset : 0
      // Center the box horizontally relative to the circle, position below with overlap offset
      return `translate(${-boxDimensions.width / 2}, ${summaryOffsetY + yOffset})`
    })
    .style('cursor', 'pointer') // All visible summaries can be hovered for foreground
    .on('mouseenter', function (_event: MouseEvent, d: PositionedNode) {
      // Bring this summary to foreground when hovered (works for all visible summaries)
      onSummaryForeground(d.node.data.id)
    })
    .on('mouseleave', function () {
      // Remove from foreground when mouse leaves
      onSummaryForeground(null)
    })

  // Create a clipPath for each expanded box (no animation, render immediately)
  expandedGroups.each(function (d: PositionedNode) {
    const group = d3.select<SVGGElement, PositionedNode>(this)
    const boxDimensions = calculateBoxDimensions(d.node.data.summary)
    const clipId = `summary-clip-${d.node.data.id}`

    // Remove existing clipPath if any
    group.selectAll(`#${clipId}`).remove()

    // Create clipPath - all summaries render immediately without animation
    const clipPath = group.append('clipPath').attr('id', clipId)
    clipPath.append('rect')
      .attr('x', 0)
      .attr('y', 0)
      .attr('height', boxDimensions.height)
      .attr('width', boxDimensions.width)
  })

  expandedGroups
    .append('rect')
    .attr('class', 'summary-box-bg')
    .attr('clip-path', (d: PositionedNode) => `url(#summary-clip-${d.node.data.id})`)
    .attr('width', (d: PositionedNode) => {
      const boxDimensions = calculateBoxDimensions(d.node.data.summary)
      return boxDimensions.width
    })
    .attr('height', (d: PositionedNode) => {
      const boxDimensions = calculateBoxDimensions(d.node.data.summary)
      return boxDimensions.height
    })
    .attr('rx', 8)
    .attr('ry', 8)
    .attr('fill', getCssVar('--color-surface-elevated'))
    .attr('stroke', (d: PositionedNode) => {
      // Highlight border when this summary is in foreground
      return foregroundSummaryId === d.node.data.id ? getCssVar('--color-accent') : getCssVar('--color-border')
    })
    .attr('stroke-width', (d: PositionedNode) => {
      return foregroundSummaryId === d.node.data.id ? 2 : 1
    })
    .attr('opacity', 0.95)

  // Add summary text (only for expanded summaries)
  summaryGroupsMerged.selectAll('.summary-text').remove()
  expandedGroups
    .append('foreignObject')
    .attr('class', 'summary-text')
    .attr('clip-path', (d: PositionedNode) => `url(#summary-clip-${d.node.data.id})`)
    .attr('x', 10)
    .attr('y', 10)
    .attr('width', (d: PositionedNode) => {
      const boxDimensions = calculateBoxDimensions(d.node.data.summary)
      return boxDimensions.width - 20
    })
    .attr('height', (d: PositionedNode) => {
      const boxDimensions = calculateBoxDimensions(d.node.data.summary)
      return boxDimensions.height - 20
    })
    .style('pointer-events', 'none')
    .append('xhtml:div')
    .style('font-size', '12px')
    .style('font-family', 'system-ui, -apple-system, sans-serif')
    .style('color', getCssVar('--color-text'))
    .style('line-height', '1.4')
    .style('overflow', 'hidden')
    .style('text-overflow', 'ellipsis')
    .style('display', 'flex')
    .style('align-items', 'center')
    .style('justify-content', 'center')
    .style('text-align', 'center')
    .style('width', '100%')
    .style('height', '100%')
    .text((d: PositionedNode) => d.node.data.summary)
}
