"""State manager for conversation tree persistence."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from models import TreeNode


class StateManager:
    """Manages conversation tree state with JSON file persistence."""

    def __init__(self, file_path: str | Path) -> None:
        """
        Initialize state manager.

        Args:
            file_path: Path to JSON file for persistence
        """
        self.file_path = Path(file_path)
        self.root: TreeNode | None = None
        self.current_node: TreeNode | None = None
        self.current_branch_id: str = "main"
        self.node_map: dict[str, TreeNode] = {}  # Fast lookup by node ID

    def initialize_root(self, agent_name: str, message: str) -> TreeNode:
        """
        Initialize the tree with a root node.

        Args:
            agent_name: Name of the agent sending the first message
            message: Content of the first message

        Returns:
            The created root node
        """
        node_id = self._generate_node_id()
        self.root = TreeNode(
            id=node_id,
            agent_name=agent_name,
            message=message,
            parent=None,
            children=[],
            is_active=True,
            branch_id=self.current_branch_id,
            timestamp=datetime.now(),
        )
        self.current_node = self.root
        self.node_map[node_id] = self.root
        return self.root

    def add_node(self, agent_name: str, message: str) -> TreeNode | None:
        """
        Add a node to the current active branch.
        If the agent is a GroupChatManager, increment a counter on the current node
        instead of adding a new node.

        Args:
            agent_name: Name of the agent sending the message
            message: Content of the message

        Returns:
            The created node, or None if a counter was incremented instead

        Raises:
            RuntimeError: If tree has not been initialized
        """
        if self.current_node is None:
            raise RuntimeError("Tree not initialized. Call initialize_root() first.")

        if "GroupChatManager" in agent_name:
            self.current_node.gcm_count += 1
            return None

        node_id = self._generate_node_id()
        new_node = TreeNode(
            id=node_id,
            agent_name=agent_name,
            message=message,
            parent=self.current_node.id,
            children=[],
            is_active=True,
            branch_id=self.current_branch_id,
            timestamp=datetime.now(),
        )

        self.current_node.children.append(new_node)
        self.current_node = new_node
        self.node_map[node_id] = new_node
        return new_node

    def create_branch(self, trim_count: int, user_message: str, user_name: str = "User") -> TreeNode:
        """
        Create a new branch by traversing up the tree and adding a user message.

        Args:
            trim_count: Number of nodes to traverse up from current position
            user_message: Content of the user's message
            user_name: Name to use for the user node (default: "User")

        Returns:
            The created user message node

        Raises:
            RuntimeError: If tree not initialized or trim_count exceeds tree depth
        """
        if self.current_node is None or self.root is None:
            raise RuntimeError("Tree not initialized. Call initialize_root() first.")

        # Store reference to current node before traversing
        old_current = self.current_node

        # Calculate effective trim_count including hidden GCM messages
        effective_trim_count = trim_count
        temp_node = self.current_node
        for _ in range(trim_count):
            if temp_node.parent:
                parent_node = self.node_map.get(temp_node.parent)
                if parent_node:
                    effective_trim_count += temp_node.gcm_count
                    temp_node = parent_node
                else:
                    break
            else:
                break
        
        # Traverse up the tree by the effective_trim_count
        branch_point = self.current_node
        for _ in range(effective_trim_count):
            if branch_point.parent is None:
                raise RuntimeError(
                    f"trim_count {trim_count} (effective: {effective_trim_count}) exceeds tree depth."
                )
            branch_point = self.node_map[branch_point.parent]

        # Mark all descendants of the old branch as inactive
        # Find which child of branch_point leads to the old current node
        old_branch_child = self._find_old_branch_child(branch_point, old_current)
        if old_branch_child is not None:
            self._mark_descendants_inactive(old_branch_child)

        # Generate new branch ID
        self.current_branch_id = self._generate_branch_id()

        # Create user message node as a new child of the branch point
        node_id = self._generate_node_id()
        user_node = TreeNode(
            id=node_id,
            agent_name=user_name,
            message=user_message,
            parent=branch_point.id,
            children=[],
            is_active=True,
            branch_id=self.current_branch_id,
            timestamp=datetime.now(),
        )

        branch_point.children.append(user_node)
        self.current_node = user_node
        self.node_map[node_id] = user_node
        return user_node

    def _mark_descendants_inactive(self, node: TreeNode) -> None:
        """
        Recursively mark a node and all its descendants as inactive.

        Args:
            node: Starting node to mark inactive
        """
        node.is_active = False
        for child in node.children:
            self._mark_descendants_inactive(child)

    def _find_old_branch_child(self, branch_point: TreeNode, target_node: TreeNode) -> TreeNode | None:
        """
        Find which child of branch_point is an ancestor of target_node.

        This is used during branching to identify the old branch that should be marked inactive.

        Args:
            branch_point: The node we're branching from
            target_node: The node we're trying to reach (old current_node)

        Returns:
            The child of branch_point that leads to target_node, or None if not found
        """
        # If branch_point has no children, there's no old branch
        if not branch_point.children:
            return None

        # Check each child of branch_point
        for child in branch_point.children:
            # If this child is the target, or is an ancestor of the target, this is the old branch
            if child.id == target_node.id or self._is_ancestor_of(child, target_node):
                return child

        return None

    def _is_ancestor_of(self, potential_ancestor: TreeNode, descendant: TreeNode) -> bool:
        """
        Check if potential_ancestor is an ancestor of descendant.

        Args:
            potential_ancestor: The node that might be an ancestor
            descendant: The node to check

        Returns:
            True if potential_ancestor is an ancestor of descendant, False otherwise
        """
        current = descendant
        while current.parent is not None:
            parent = self.node_map.get(current.parent)
            if parent is None:
                break
            if parent.id == potential_ancestor.id:
                return True
            current = parent
        return False

    def get_tree_dict(self) -> dict[str, Any]:
        """
        Get the tree as a dictionary for serialization.

        Returns:
            Dictionary representation of the tree

        Raises:
            RuntimeError: If tree has not been initialized
        """
        if self.root is None:
            raise RuntimeError("Tree not initialized. Call initialize_root() first.")

        return {
            "root": self._node_to_dict(self.root),
            "current_branch_id": self.current_branch_id,
        }

    def _node_to_dict(self, node: TreeNode) -> dict[str, Any]:
        """
        Convert a node and its children to dictionary format.

        Args:
            node: Node to convert

        Returns:
            Dictionary representation
        """
        return {
            "id": node.id,
            "agent_name": node.agent_name,
            "message": node.message,
            "parent": node.parent,
            "children": [self._node_to_dict(child) for child in node.children],
            "is_active": node.is_active,
            "branch_id": node.branch_id,
            "timestamp": node.timestamp.isoformat(),
            "gcm_count": node.gcm_count,
        }

    def save_to_file(self) -> None:
        """
        Save the current tree state to the configured JSON file.

        Uses atomic write (write to temp file, then rename) to prevent corruption.

        Raises:
            RuntimeError: If tree has not been initialized
        """
        if self.root is None:
            raise RuntimeError("Tree not initialized. Nothing to save.")

        tree_dict = self.get_tree_dict()

        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file, then rename
        temp_path = self.file_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(tree_dict, f, indent=2, ensure_ascii=False)

        # Atomic rename (overwrites existing file on Unix-like systems)
        temp_path.replace(self.file_path)

    def load_from_file(self) -> None:
        """
        Load tree state from the configured JSON file.

        Raises:
            FileNotFoundError: If the state file does not exist
            ValueError: If the file contains invalid data
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"State file not found: {self.file_path}")

        with self.file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if "root" not in data:
            raise ValueError("Invalid state file: missing 'root' key")

        self.current_branch_id = data.get("current_branch_id", "main")
        self.root = self._dict_to_node(data["root"])
        self.node_map = {}
        self._build_node_map(self.root)

        # Set current_node to the last node in the current branch
        self.current_node = self._find_last_active_node()

    def _dict_to_node(self, data: dict[str, Any]) -> TreeNode:
        """
        Convert dictionary to TreeNode recursively.

        Args:
            data: Dictionary representation of node

        Returns:
            Reconstructed TreeNode
        """
        children = [self._dict_to_node(child) for child in data.get("children", [])]

        return TreeNode(
            id=data["id"],
            agent_name=data["agent_name"],
            message=data["message"],
            parent=data.get("parent"),
            children=children,
            is_active=data.get("is_active", True),
            branch_id=data.get("branch_id", "main"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            gcm_count=data.get("gcm_count", 0),
        )

    def _build_node_map(self, node: TreeNode) -> None:
        """
        Build node_map for fast lookups by traversing the tree.

        Args:
            node: Current node to add to map
        """
        self.node_map[node.id] = node
        for child in node.children:
            self._build_node_map(child)

    def _find_last_active_node(self) -> TreeNode:
        """
        Find the last node in the current active branch.

        Returns:
            The last active node

        Raises:
            RuntimeError: If tree has no root
        """
        if self.root is None:
            raise RuntimeError("Tree not initialized")

        node = self.root
        while True:
            active_children = [child for child in node.children if child.is_active]
            if not active_children:
                return node
            # If multiple active children, pick the one matching current_branch_id
            matching = [c for c in active_children if c.branch_id == self.current_branch_id]
            node = matching[0] if matching else active_children[-1]

    def _generate_node_id(self) -> str:
        """Generate a unique node ID."""
        return f"node_{uuid.uuid4().hex[:12]}"

    def _generate_branch_id(self) -> str:
        """Generate a unique branch ID."""
        return f"branch_{uuid.uuid4().hex[:8]}"

    def reset(self) -> None:
        """Reset the state manager to initial state."""
        self.root = None
        self.current_node = None
        self.current_branch_id = "main"
        self.node_map = {}

    def get_current_node(self) -> TreeNode | None:
        """Get the current active node."""
        return self.current_node

    def get_root(self) -> TreeNode | None:
        """Get the root node."""
        return self.root

    def find_node_by_id(self, node_id: str) -> TreeNode | None:
        """
        Find a node by its ID using the node_map.

        Args:
            node_id: ID of the node to find

        Returns:
            The node if found, None otherwise
        """
        return self.node_map.get(node_id)

    def get_active_branch_path(self) -> list[TreeNode]:
        """
        Get the path of nodes from root to current node in the active branch.

        Returns:
            List of nodes from root to current node

        Raises:
            RuntimeError: If tree has not been initialized
        """
        if self.root is None or self.current_node is None:
            raise RuntimeError("Tree not initialized")

        path: list[TreeNode] = []
        node: TreeNode | None = self.current_node

        while node is not None:
            path.append(node)
            if node.parent is None:
                break
            node = self.node_map.get(node.parent)

        return list(reversed(path))

    def get_all_branches(self) -> dict[str, list[TreeNode]]:
        """
        Get all branches in the tree, including inactive ones.

        Returns:
            Dictionary mapping branch_id to list of nodes in that branch
        """
        if self.root is None:
            return {}

        branches: dict[str, list[TreeNode]] = {}

        def collect_branches(node: TreeNode) -> None:
            if node.branch_id not in branches:
                branches[node.branch_id] = []
            branches[node.branch_id].append(node)

            for child in node.children:
                collect_branches(child)

        collect_branches(self.root)
        return branches

    def get_subtree(self, node_id: str, max_depth: int | None = None) -> TreeNode | None:
        """
        Get a subtree starting from a specific node.

        Args:
            node_id: ID of the root node for the subtree
            max_depth: Maximum depth to traverse (None for unlimited)

        Returns:
            The subtree root node, or None if node not found
        """
        node = self.find_node_by_id(node_id)
        if node is None:
            return None

        if max_depth == 0:
            # Return node without children
            return TreeNode(
                id=node.id,
                agent_name=node.agent_name,
                message=node.message,
                parent=node.parent,
                children=[],
                is_active=node.is_active,
                branch_id=node.branch_id,
                timestamp=node.timestamp,
            )

        if max_depth is None:
            # Return full subtree
            return node

        # Return subtree with limited depth
        def limit_depth(n: TreeNode, depth: int) -> TreeNode:
            if depth == 0:
                return TreeNode(
                    id=n.id,
                    agent_name=n.agent_name,
                    message=n.message,
                    parent=n.parent,
                    children=[],
                    is_active=n.is_active,
                    branch_id=n.branch_id,
                    timestamp=n.timestamp,
                )
            return TreeNode(
                id=n.id,
                agent_name=n.agent_name,
                message=n.message,
                parent=n.parent,
                children=[limit_depth(child, depth - 1) for child in n.children],
                is_active=n.is_active,
                branch_id=n.branch_id,
                timestamp=n.timestamp,
            )

        return limit_depth(node, max_depth)

    def get_tree_depth(self) -> int:
        """
        Calculate the maximum depth of the tree.

        Returns:
            Maximum depth (root is depth 0)

        Raises:
            RuntimeError: If tree has not been initialized
        """
        if self.root is None:
            raise RuntimeError("Tree not initialized")

        def calculate_depth(node: TreeNode) -> int:
            if not node.children:
                return 0
            return 1 + max(calculate_depth(child) for child in node.children)

        return calculate_depth(self.root)

    def get_tree_breadth(self) -> int:
        """
        Calculate the maximum breadth (number of children) at any level.

        Returns:
            Maximum breadth of the tree

        Raises:
            RuntimeError: If tree has not been initialized
        """
        if self.root is None:
            raise RuntimeError("Tree not initialized")

        max_breadth = 0

        def traverse(node: TreeNode) -> None:
            nonlocal max_breadth
            if len(node.children) > max_breadth:
                max_breadth = len(node.children)
            for child in node.children:
                traverse(child)

        traverse(self.root)
        return max_breadth

    def get_recent_nodes(self, count: int) -> list[TreeNode]:
        """
        Get the most recent nodes in the active branch.

        Args:
            count: Number of recent nodes to return

        Returns:
            List of recent nodes, newest first

        Raises:
            RuntimeError: If tree has not been initialized
        """
        if self.current_node is None or self.root is None:
            raise RuntimeError("Tree not initialized")

        path = self.get_active_branch_path()
        # Return last 'count' nodes in reverse order (newest first)
        return list(reversed(path[-count:]))

    def get_ancestors(self, node_id: str) -> list[TreeNode]:
        """
        Get all ancestor nodes of a given node.

        Args:
            node_id: ID of the node to find ancestors for

        Returns:
            List of ancestor nodes from root to node (excluding the node itself)

        Raises:
            ValueError: If node not found
        """
        node = self.find_node_by_id(node_id)
        if node is None:
            raise ValueError(f"Node with id {node_id} not found")

        ancestors: list[TreeNode] = []
        current = node

        while current.parent is not None:
            parent = self.node_map.get(current.parent)
            if parent is None:
                break
            ancestors.append(parent)
            current = parent

        return list(reversed(ancestors))

    def get_descendants(self, node_id: str) -> list[TreeNode]:
        """
        Get all descendant nodes of a given node.

        Args:
            node_id: ID of the node to find descendants for

        Returns:
            List of all descendants (depth-first order)

        Raises:
            ValueError: If node not found
        """
        node = self.find_node_by_id(node_id)
        if node is None:
            raise ValueError(f"Node with id {node_id} not found")

        descendants: list[TreeNode] = []

        def collect_descendants(n: TreeNode) -> None:
            for child in n.children:
                descendants.append(child)
                collect_descendants(child)

        collect_descendants(node)
        return descendants

    def get_siblings(self, node_id: str) -> list[TreeNode]:
        """
        Get all sibling nodes of a given node.

        Args:
            node_id: ID of the node to find siblings for

        Returns:
            List of sibling nodes (excluding the node itself)

        Raises:
            ValueError: If node not found
        """
        node = self.find_node_by_id(node_id)
        if node is None:
            raise ValueError(f"Node with id {node_id} not found")

        if node.parent is None:
            # Root node has no siblings
            return []

        parent = self.node_map.get(node.parent)
        if parent is None:
            return []

        # Return all children of parent except the node itself
        return [child for child in parent.children if child.id != node_id]

    def get_visualization_data(
        self, center_node_id: str | None = None, max_height: int = 3
    ) -> dict[str, Any]:
        """
        Get data structured for tree visualization in the frontend.

        This returns a subtree centered around a specific node (default: last user message)
        with a maximum height, suitable for the default tree view.

        Args:
            center_node_id: ID of the node to center on (None for last user message)
            max_height: Maximum height of visible subtree (default: 3)

        Returns:
            Dictionary containing visualization data with keys:
                - center_node: The node at the center
                - visible_nodes: List of visible nodes
                - active_path: Path from root to current node
                - tree_depth: Total depth of the tree
                - tree_breadth: Maximum breadth of the tree

        Raises:
            RuntimeError: If tree has not been initialized
        """
        if self.root is None or self.current_node is None:
            raise RuntimeError("Tree not initialized")

        # Find center node (last user message if not specified)
        if center_node_id is None:
            # Find the last user message in the active branch
            path = self.get_active_branch_path()
            center = None
            for node in reversed(path):
                if node.agent_name.lower() in ["user", "usercontrol", "usercontrolagent"]:
                    center = node
                    break
            if center is None:
                center = self.current_node
        else:
            center = self.find_node_by_id(center_node_id)
            if center is None:
                raise ValueError(f"Center node {center_node_id} not found")

        # Get visible nodes within max_height from center
        visible_nodes: list[TreeNode] = [center]

        # Add ancestors up to max_height/2 levels up
        ancestors_to_add = max_height // 2
        current = center
        for _ in range(ancestors_to_add):
            if current.parent is None:
                break
            parent = self.node_map.get(current.parent)
            if parent is None:
                break
            visible_nodes.append(parent)
            current = parent

        # Add descendants up to max_height/2 levels down
        descendants_to_add = max_height - ancestors_to_add

        def add_descendants(node: TreeNode, levels: int) -> None:
            if levels <= 0:
                return
            for child in node.children:
                if child not in visible_nodes:
                    visible_nodes.append(child)
                add_descendants(child, levels - 1)

        add_descendants(center, descendants_to_add)

        return {
            "center_node": center,
            "visible_nodes": visible_nodes,
            "active_path": self.get_active_branch_path(),
            "tree_depth": self.get_tree_depth(),
            "tree_breadth": self.get_tree_breadth(),
            "current_branch_id": self.current_branch_id,
        }

    def get_node_level(self, node_id: str) -> int:
        """
        Get the level (depth from root) of a node.

        Args:
            node_id: ID of the node

        Returns:
            Level of the node (root is level 0)

        Raises:
            ValueError: If node not found
        """
        node = self.find_node_by_id(node_id)
        if node is None:
            raise ValueError(f"Node with id {node_id} not found")

        level = 0
        current = node

        while current.parent is not None:
            level += 1
            parent = self.node_map.get(current.parent)
            if parent is None:
                break
            current = parent

        return level

    def count_active_nodes(self) -> int:
        """
        Count the number of active nodes in the tree.

        Returns:
            Number of active nodes

        Raises:
            RuntimeError: If tree has not been initialized
        """
        if self.root is None:
            raise RuntimeError("Tree not initialized")

        count = 0

        def traverse(node: TreeNode) -> None:
            nonlocal count
            if node.is_active:
                count += 1
            for child in node.children:
                traverse(child)

        traverse(self.root)
        return count

    def count_total_nodes(self) -> int:
        """
        Count the total number of nodes in the tree.

        Returns:
            Total number of nodes

        Raises:
            RuntimeError: If tree has not been initialized
        """
        if self.root is None:
            raise RuntimeError("Tree not initialized")

        return len(self.node_map)

    def get_branch_point(self, node_id: str) -> TreeNode | None:
        """
        Find the branch point (node with multiple children) closest to the given node.

        Args:
            node_id: ID of the node to start searching from

        Returns:
            The closest branch point node, or None if no branch point found

        Raises:
            ValueError: If node not found
        """
        node = self.find_node_by_id(node_id)
        if node is None:
            raise ValueError(f"Node with id {node_id} not found")

        current = node
        while current is not None:
            if len(current.children) > 1:
                return current
            if current.parent is None:
                return None
            current = self.node_map.get(current.parent)

        return None
