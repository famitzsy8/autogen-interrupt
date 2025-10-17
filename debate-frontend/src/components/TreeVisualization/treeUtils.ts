/**
 * Tree utility functions for conversation tree visualization.
 *
 * Provides helper functions for:
 * - Converting TreeNode data to D3 hierarchy format
 * - Finding active paths in the tree
 * - Calculating tree dimensions
 * - Managing node visibility
 */

import * as d3 from 'd3'
import type { TreeNode } from '../../types'

/**
 * D3 hierarchy node type with custom data.
 */
export interface D3TreeNode extends d3.HierarchyPointNode<TreeNode> {
  _children?: D3TreeNode[]
  x0?: number
  y0?: number
}

/**
 * Configuration for tree layout calculations.
 */
export interface TreeConfig {
  nodeWidth: number
  nodeHeight: number
  horizontalSpacing: number
  verticalSpacing: number
}

/**
 * Default tree configuration values.
 */
export const DEFAULT_TREE_CONFIG: TreeConfig = {
  nodeWidth: 120,
  nodeHeight: 60,
  horizontalSpacing: 120,
  verticalSpacing: 150,
}

/**
 * Convert TreeNode to D3 hierarchy format.
 * @param treeNode - Root node from the conversation tree
 * @returns D3 hierarchy root node
 */
export function convertToD3Hierarchy(treeNode: TreeNode): D3TreeNode {
  const hierarchy = d3.hierarchy(treeNode, (d) => d.children)
  return hierarchy as D3TreeNode
}

/**
 * Find all nodes in the active branch.
 * @param root - D3 hierarchy root node
 * @param currentBranchId - Current active branch ID
 * @returns Set of node IDs in the active branch
 */
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
 * Find nodes that should be visible based on max height constraint.
 * Ensures that all branch points and their children are visible to show full conversation history.
 * @param root - D3 hierarchy root node
 * @param centerNodeId - Node to center the view on
 * @param maxHeight - Maximum height of subtree to show
 * @returns Set of visible node IDs
 */
export function findVisibleNodes(
  root: D3TreeNode,
  centerNodeId: string | null,
  maxHeight: number
): Set<string> {
  const visibleNodeIds = new Set<string>()

  // Find the center node
  let centerNode: D3TreeNode | null = null
  root.each((node: D3TreeNode) => {
    if (node.data.id === centerNodeId) {
      centerNode = node
    }
  })

  if (!centerNode) {
    // If no center node specified, show entire tree (all nodes)
    root.each((node: D3TreeNode) => {
      visibleNodeIds.add(node.data.id)
    })
    return visibleNodeIds
  }

  // TypeScript needs explicit assertion that centerNode is not null after the check
  const validCenterNode: D3TreeNode = centerNode

  // Add center node
  visibleNodeIds.add(validCenterNode.data.id)

  // Add ALL ancestors up to root
  let current = validCenterNode.parent
  while (current) {
    const d3Current = current as D3TreeNode
    visibleNodeIds.add(d3Current.data.id)

    // If this node has multiple children (branch point), include ALL children and their descendants
    // This ensures we show all branches, not just the active one
    if (d3Current.children && d3Current.children.length > 1) {
      d3Current.children.forEach((child) => {
        const d3Child = child as D3TreeNode
        // Add all descendants of each branch
        addAllDescendants(d3Child, visibleNodeIds)
      })
    }

    current = d3Current.parent
  }

  // Add descendants of center node up to max height
  function addDescendants(node: D3TreeNode, remainingHeight: number): void {
    if (remainingHeight <= 0) return

    if (node.children) {
      node.children.forEach((child) => {
        const d3Child = child as D3TreeNode
        visibleNodeIds.add(d3Child.data.id)
        addDescendants(d3Child, remainingHeight - 1)
      })
    }
  }

  addDescendants(validCenterNode, maxHeight)

  return visibleNodeIds
}

/**
 * Helper function to add all descendants of a node recursively.
 * @param node - Starting node
 * @param visibleSet - Set to add node IDs to
 */
function addAllDescendants(node: D3TreeNode, visibleSet: Set<string>): void {
  visibleSet.add(node.data.id)

  if (node.children) {
    node.children.forEach((child) => {
      addAllDescendants(child as D3TreeNode, visibleSet)
    })
  }
}

/**
 * Collapse nodes that are not in the visible set.
 * @param node - D3 hierarchy node to process
 * @param visibleNodeIds - Set of IDs that should remain visible
 */
export function collapseInvisibleNodes(node: D3TreeNode, visibleNodeIds: Set<string>): void {
  if (node.children) {
    const shouldCollapseChildren = !visibleNodeIds.has(node.data.id)

    if (shouldCollapseChildren) {
      // Store children and hide them
      node._children = node.children as unknown as D3TreeNode[]
      node.children = undefined
    } else {
      // Process visible children recursively
      node.children.forEach((child) => {
        collapseInvisibleNodes(child as unknown as D3TreeNode, visibleNodeIds)
      })
    }
  }
}

/**
 * Expand all collapsed nodes.
 * @param node - D3 hierarchy node to process
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

/**
 * Calculate the opacity for a node based on its active state.
 * @param node - Tree node data
 * @param isInActivePath - Whether node is in the active branch
 * @returns Opacity value (0-1)
 */
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
    if (node.data.agent_name === 'User' && node.data.timestamp > latestTimestamp) {
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
