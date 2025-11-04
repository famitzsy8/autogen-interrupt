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

// TODO: get rid of the height constraint:
// In this function equivalent in dr-frontend we set the policy on how to
// display the entire tree based on the maxHeight policy. I want to get rid of this maxHeight constraint
// such that we really have a very simple display logic that doesn't need to factor in the maxHeight:

// when streaming: per default center into the latest node that has been added to the conversation tree
// when streaming but navigating the conversation tree with the mouse: disable automatic re-centering with a no activity timeout of 15 seconds
//      after which we re-center on the stream
// when interrupted: don't recenter at all (dr-backend has this already implemented)

export function findVisibleNodes(
    root: D3TreeNode,
    centerNodeId: string | null,
    maxHeight: number
): Set<string> {
    
}

function addAllDescendants(node: D3TreeNode, visibleSet: Set<string>): void {

}

export function collapseInvisibleNodes(node: D3TreeNode, visibleNodeIds: Set<string>): void {

}

export function expandAllNodes(node: D3TreeNode): void {

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
 * Find the last message node in the active branch.
 * @param root - D3 hierarchy root node
 * @param currentBranchId - ID of the active branch
 * @returns The last message node in the active branch or null
 */
export function findLastMessageNode(root: D3TreeNode, currentBranchId: string): D3TreeNode | null {
    let lastNode: D3TreeNode | null = null;
    let latestTimestamp = '';

    root.each((node) => {
        if (node.data.branch_id === currentBranchId && node.data.is_active) {
            if (node.data.timestamp > latestTimestamp) {
                latestTimestamp = node.data.timestamp;
                lastNode = node;
            }
        }
    });

    return lastNode;
}

/**
 * Find the last user message node in the tree.
 * @param root - D3 hierarchy root node
 * @returns The last user message node or null
 */
export function findLastUserMessageNode(root: D3TreeNode): D3TreeNode | null {
    let lastUserNode: D3TreeNode | null = null
    let latestTimestamp = ''
  
    root.each((node) => {
      if (node.data.agent_name === 'You' && node.data.timestamp > latestTimestamp) { // TODO: make sure this is consistent with the rest of the user agent messages (all should be named "You")
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
  
    root.each((node) => {
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
    root.each(() => count++)
    return count
}
  