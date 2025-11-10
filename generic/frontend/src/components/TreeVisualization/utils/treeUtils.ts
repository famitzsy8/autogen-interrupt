import * as d3 from 'd3'
import type { TreeNode } from '../../../types'

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

    console.log('[treeUtils] Finding last active node in branch:', currentBranchId)

    root.each((node: D3TreeNode) => {
        if (node.data.branch_id === currentBranchId && node.data.is_active) {
            if (node.data.timestamp > latestTimestamp) {
                console.log(`[treeUtils]   Found newer node: id=${node.data.id}, type=${node.data.node_type}, timestamp=${node.data.timestamp}`)
                latestTimestamp = node.data.timestamp;
                lastNode = node;
            }
        }
    });

    if (lastNode) {
        const activeNode = lastNode as D3TreeNode
        console.log(`[treeUtils] Last active node: id=${activeNode.data.id}, type=${activeNode.data.node_type}`)
    } else {
        console.log('[treeUtils] No active node found!')
    }

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
  
