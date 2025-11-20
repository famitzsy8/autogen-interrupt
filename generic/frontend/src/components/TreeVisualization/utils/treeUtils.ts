import * as d3 from 'd3'
import type { TreeNode, StateUpdate } from '../../../types'

export interface D3TreeNode extends d3.HierarchyPointNode<TreeNode> {
    _children?: D3TreeNode[]
    x0?: number
    y0?: number
}

export interface TreeConfig {
    nodeWidth: number
    nodeHeight: number
    horizontalSpacing: number
    verticalSpacing: number
}

export const DEFAULT_TREE_CONFIG: TreeConfig = {
    nodeWidth: 120,
    nodeHeight: 60,
    horizontalSpacing: 120,
    verticalSpacing: 150,
}

export function convertToD3Hierarchy(treeNode: TreeNode): D3TreeNode {
    const hierarchy = d3.hierarchy(treeNode, (d) => d.children)
    return hierarchy as D3TreeNode
}

// Finds all nodes in the active branch
export function findActivePath(root: D3TreeNode, currentBranchId: string): Set<string> {
    const activeNodeIds = new Set<string>()

    function traverse(node: D3TreeNode): void {
        if (node.data.branch_id === currentBranchId && node.data.is_active) {
            activeNodeIds.add(node.data.id)
        }
        if (node.children) {
            node.children.forEach(traverse)
        }
    }

    traverse(root)
    return activeNodeIds
}

/**
 * Find all visible nodes in the tree.
 * Shows the entire tree without any height constraints.
 */
export function findVisibleNodes(root: D3TreeNode): Set<string> {
    const visibleNodeIds = new Set<string>()

    // Show all nodes in the tree
    root.each((node: D3TreeNode) => {
        visibleNodeIds.add(node.data.id)
    })

    return visibleNodeIds
}

/**
 * Expand all collapsed nodes to show the full tree.
 */
export function expandAllNodes(node: D3TreeNode): void {
    if (node._children) {
        node.children = node._children as unknown as d3.HierarchyPointNode<TreeNode>[]
        node._children = undefined
    }

    if (node.children) {
        node.children.forEach((child) => {
            expandAllNodes(child as unknown as D3TreeNode)
        })
    }
}

export function calculateNodeOpacity(node: TreeNode, isInActivePath: boolean): number {
    if (!node.is_active) {
      return 0.3 // Diminished opacity for inactive branches
    }
    return isInActivePath ? 1.0 : 0.6
}

/**
 * Create a diagonal path for GitHub-style branch arrows.
 * @param source - Source point {x, y}
 * @param target - Target point {x, y}
 * @returns SVG path string
 */
export function createBranchPath(
    source: { x: number; y: number },
    target: { x: number; y: number }
): string {

    const midY = (source.y + target.y) / 2
  
    return `M ${source.y} ${source.x}
            C ${midY} ${source.x},
              ${midY} ${target.x},
              ${target.y} ${target.x}`
}

/**
 * Calculate the bounding box of the tree.
 * @param nodes - Array of D3 hierarchy nodes
 * @returns Bounding box {minX, maxX, minY, maxY}
 */
export function calculateTreeBounds(
    nodes: D3TreeNode[]
  ): { minX: number; maxX: number; minY: number; maxY: number } {
    let minX = Infinity
    let maxX = -Infinity
    let minY = Infinity
    let maxY = -Infinity
  
    nodes.forEach((node) => {
      if (node.x < minX) minX = node.x
      if (node.x > maxX) maxX = node.x
      if (node.y < minY) minY = node.y
      if (node.y > maxY) maxY = node.y
    })
  
    return { minX, maxX, minY, maxY }
}

/**
 * Find the last active node in the current branch (regardless of node type).
 * This function finds the most recently created node in the active branch,
 * which could be a message, tool_call, or tool_execution node.
 *
 * @param root - D3 hierarchy root node
 * @param currentBranchId - ID of the active branch
 * @returns The last active node in the current branch or null
 */
export function findLastMessageNode(root: D3TreeNode, currentBranchId: string): D3TreeNode | null {
    let lastNode: D3TreeNode | null = null
    let latestTimestamp = '';


    root.each((node: D3TreeNode) => {
        if (node.data.branch_id === currentBranchId && node.data.is_active) {
            if (node.data.timestamp > latestTimestamp) {
                latestTimestamp = node.data.timestamp;
                lastNode = node;
            }
        }
    });

    return lastNode
}

/**
 * Find the last user message node in the tree.
 * User messages have agent_name "You" as set by the backend UserControlAgent.
 * @param root - D3 hierarchy root node
 * @returns The last user message node or null
 */
export function findLastUserMessageNode(root: D3TreeNode): D3TreeNode | null {
    let lastUserNode: D3TreeNode | null = null
    let latestTimestamp = ''

    root.each((node: D3TreeNode) => {
      if (node.data.agent_name === 'You' && node.data.timestamp > latestTimestamp) {
        lastUserNode = node
        latestTimestamp = node.data.timestamp
      }
    })

    return lastUserNode
}


/**
 * Get the depth of a tree.
 * @param root - D3 hierarchy root node
 * @returns Maximum depth of the tree
 */
export function getTreeDepth(root: D3TreeNode): number {
    let maxDepth = 0
  
    root.each((node: D3TreeNode) => {
      if (node.depth > maxDepth) {
        maxDepth = node.depth
      }
    })
  
    return maxDepth
}

/**
 * Count total number of nodes in the tree.
 * @param root - D3 hierarchy root node
 * @returns Total node count
 */
export function countNodes(root: D3TreeNode): number {
    let count = 0
    root.each(() => {
      count++
    })
    return count
}

/**
 * Find the most recent state update that was active when the node was created.
 * Returns the state with the latest timestamp that is less than or equal to the node's timestamp.
 *
 * @param node - The tree node to find the state for
 * @param allStateUpdates - Array of all state updates from the run
 * @returns The matching StateUpdate or undefined if no matching state found
 */
export function findStateForNode(node: TreeNode, allStateUpdates: StateUpdate[]): StateUpdate | undefined {
    // Filter states where state.timestamp <= node.timestamp
    const eligibleStates = allStateUpdates.filter(state => state.timestamp <= node.timestamp)

    // If no states match, return undefined
    if (eligibleStates.length === 0) {
        return undefined
    }

    // Sort by timestamp descending and return the first (most recent)
    eligibleStates.sort((a, b) => b.timestamp.localeCompare(a.timestamp))

    return eligibleStates[0]
}

/**
 * Check if a node represents user feedback or input.
 * Checks against known user agent names that indicate user interaction.
 *
 * @param node - The tree node to check
 * @returns true if the node is from a user feedback agent, false otherwise
 */
export function isUserFeedbackNode(node: TreeNode): boolean {
    const userAgentNames = ['user_proxy', 'user_control', 'you']
    const normalizedAgentName = node.agent_name.toLowerCase().trim()

    return userAgentNames.includes(normalizedAgentName)
}

/**
 * Format the raw state_of_run text for display in the UI.
 * Performs basic text cleanup without parsing or transforming the content.
 *
 * @param text - Raw state_of_run text from StateUpdate
 * @returns Formatted text suitable for display
 */
export function formatStateOfRunForDisplay(text: string): string {
    // Trim leading and trailing whitespace
    let formatted = text.trim()

    // Replace multiple consecutive newlines (3+) with double newlines for cleaner display
    formatted = formatted.replace(/\n{3,}/g, '\n\n')

    return formatted
}

/**
 * Extract all unique agent names from the tree in order of first appearance.
 * Performs depth-first traversal to maintain consistent ordering.
 * @param root - Root TreeNode of the conversation tree
 * @returns Sorted array of unique agent names
 */
export function extractAgentNames(root: TreeNode): string[] {
    const agentNamesSet = new Set<string>()

    function traverse(node: TreeNode): void {
        agentNamesSet.add(node.agent_name)
        if (node.children) {
            node.children.forEach(traverse)
        }
    }

    traverse(root)
    return Array.from(agentNamesSet).sort()
}

/**
 * Calculate the depth of a specific node in the tree.
 * Depth is measured as distance from root (root = 0, immediate children = 1, etc.).
 * Used for x-axis positioning in visualization (depth * horizontalSpacing).
 * @param root - Root TreeNode of the conversation tree
 * @param nodeId - ID of the node to find
 * @returns Depth of the node, or null if node not found
 */
export function calculateNodeDepth(root: TreeNode, nodeId: string): number | null {
    function findDepth(node: TreeNode, currentDepth: number): number | null {
        if (node.id === nodeId) {
            return currentDepth
        }

        if (node.children) {
            for (const child of node.children) {
                const depth = findDepth(child, currentDepth + 1)
                if (depth !== null) {
                    return depth
                }
            }
        }

        return null
    }

    return findDepth(root, 0)
}

/**
 * Find a node in the tree by its ID.
 * Performs recursive depth-first search.
 * @param root - Root TreeNode of the conversation tree
 * @param nodeId - ID of the node to find
 * @returns The matching TreeNode or null if not found
 */
export function findNodeInTree(root: TreeNode, nodeId: string): TreeNode | null {
    if (root.id === nodeId) {
        return root
    }

    if (root.children) {
        for (const child of root.children) {
            const found = findNodeInTree(child, nodeId)
            if (found !== null) {
                return found
            }
        }
    }

    return null
}

/**
 * Find all edges (parent-child relationships) for a given node.
 * Returns edges where this node is a child (i.e., edges pointing TO this node).
 * Used for rendering links between nodes in the visualization.
 * @param node - The TreeNode to find edges for
 * @returns Array of edge objects with source (parent) and target (child) nodes
 */
export function findEdgesForNode(node: TreeNode): Array<{ source: TreeNode; target: TreeNode }> {
    const edges: Array<{ source: TreeNode; target: TreeNode }> = []

    if (node.children) {
        node.children.forEach((child) => {
            edges.push({ source: node, target: child })
        })
    }

    return edges
}
