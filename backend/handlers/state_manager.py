from __future__ import annotations

import json
from multiprocessing import active_children
from operator import add
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from models import TreeNode


class StateManager:

    def __init__(self, file_path: str | Path) -> None:

        self.file_path = Path(file_path)
        self.root: TreeNode | None = None
        self.current_node: TreeNode | None = None
        self.current_branch_id: str = "main"
        self.node_map: dict[str, TreeNode] = {}

    def initialize_root(self, agent_name: str, message: str, summary: str = "") -> TreeNode:

        node_id = self._generate_node_id()
        new_node = TreeNode(
            id=node_id,
            agent_name=agent_name,
            message=message,
            summary=summary,
            parent=None,
            children=[],
            is_active=True,
            branch_id=self.current_branch_id,
            timestamp=datetime.now(),
            node_type="message",
        )

        self.root = new_node
        self.current_node = new_node
        self.node_map[node_id] = new_node

        return new_node

    def add_node(self, agent_name: str, message: str, summary: str = "", node_type: str = "message") -> TreeNode | None:

        # TODO: This is the function where we can filter the addition of a message node based on the user

        if self.current_node is None:
            raise RuntimeError("Tree not initialized. Call initialize_root() first.")

        if "GroupChatManager" in agent_name:
            return None # TODO: make sure we don't use the gcm_count across the code and we ignore GCM messages overall

        node_id = self._generate_node_id()
        new_node = TreeNode(
            id=node_id,
            agent_name=agent_name,
            message=message,
            summary=summary,
            parent=self.current_node.id,
            children=[],
            is_active=True,
            branch_id=self.current_branch_id,
            timestamp=datetime.now(),
            node_type=node_type,
        )

        self.current_node.children.append(new_node)
        self.current_node = new_node
        self.node_map[node_id] = new_node
        return new_node

    def get_node_by_id(self, node_id: str) -> TreeNode | None:
        """Get a node by its ID from the node map."""
        return self.node_map.get(node_id)

    def create_branch(self, trim_count: int, user_message: str) -> TreeNode:

        if self.current_node is None or self.root is None:
            raise RuntimeError("Tree not initialized. Call initialize_root() first.")
        
        old_current = self.current_node

        # Count only "message" type nodes when trimming
        branch_point = self.current_node
        message_nodes_to_skip = max(0, trim_count)
        message_nodes_skipped = 0

        while message_nodes_skipped < message_nodes_to_skip:
            if branch_point.parent is None:
                raise RuntimeError(
                    f"trim_count {trim_count} exceeds available message nodes."
                )
            parent = self.node_map.get(branch_point.parent)
            if parent is None:
                raise RuntimeError(
                    f"trim_count {trim_count} exceeds available message nodes."
                )
            branch_point = parent
            # Only count "message" nodes, skip "tool_call" and "tool_execution"
            if branch_point.node_type == "message":
                message_nodes_skipped += 1
        
        old_branch_child = self._find_old_branch_child(branch_point=branch_point, branch_leaf=old_current)
        if old_branch_child is not None:
            self._mark_descendants_inactive(old_branch_child)

        node_id = self._generate_node_id()
        user_node = TreeNode(
            id=node_id,
            agent_name="You",
            message=user_message,
            summary="",  # User messages don't need summaries
            parent=branch_point.id,
            children=[],
            is_active=True,
            branch_id=self.current_branch_id,
            timestamp=datetime.now(),
            node_type="message",
        )

        branch_point.children.append(user_node)
        self.current_node = user_node
        self.node_map[node_id] = user_node
        return user_node

    def _find_old_branch_child(self, branch_point: TreeNode, branch_leaf: TreeNode) -> TreeNode | None:

        if not branch_point.children:
            return None
        
        for child in branch_point.children:
            if child.id == branch_leaf.id or self._is_ancestor_of(child, branch_leaf):
                return child
        return None
    
    def _is_ancestor_of(self, potential_ancestor: TreeNode, descendant: TreeNode) -> bool:

        current = descendant
        while current.parent is not None:
            parent = self.node_map.get(current.parent)
            if parent is None:
                break
            if parent.id == potential_ancestor.id:
                return True
            current = parent
        
        return False
    
    def _mark_descendants_inactive(self, node: TreeNode) -> None:

        node.is_active = False
        for child in node.children:
            self._mark_descendants_inactive(child)
    

    def _generate_node_id(self) -> str:
        # generate unique node ID
        return f"node_{uuid.uuid4().hex[:12]}"

    def _generate_branch_id(self) -> str:
        # generate unique branch ID
        return f"branch_{uuid.uuid4().hex[:8]}"

    def reset(self) -> None:
        # reset the state manager to the defined initial state
        self.root = None
        self.current_node = None
        self.current_branch_id = "main"
        self.node_map = {}

    def get_current_node(self) -> TreeNode | None:
        # get the leaf of the current branch
        return self.current_node

    def get_root(self) -> TreeNode | None:
        # self explanatory lol
        return self.root

    
    def get_tree_dict(self) -> dict[str, Any]:

        if self.root is None:
            raise RuntimeError("Tree not initialized. Call initialize_root() first.")
        
        return {
            "root": self._node_to_dict(self.root),
            "current_branch_id": self.current_branch_id
        }
    
    def _node_to_dict(self, node: TreeNode) -> dict[str, Any]:

        return {
            "id": node.id,
            "agent_name": node.agent_name,
            "message": node.message,
            "summary": node.summary,
            "parent": node.parent,
            "children": [self._node_to_dict(child) for child in node.children],
            "is_active": node.is_active,
            "branch_id": node.branch_id,
            "timestamp": node.timestamp.isoformat(),
        }

    def save_to_file(self) -> None:

        if self.root is None:
            raise RuntimeError("Tree not initialized. Nothing to save.")
        
        tree_dict = self.get_tree_dict()
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = self.file_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(tree_dict, f, indent=4, ensure_ascii=False)
        
        temp_path.replace(self.file_path)

    def load_from_file(self) -> None:

        if not self.file_path.exists():
            raise FileNotFoundError(f"State file not found: {self.file_path}")
        
        with self.file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        if "root" not in data:
            raise ValueError("Corrupted state file: missing 'root' key")
        
        self.current_branch_id = data.get("current_branch_id", "main")
        self.root = self._dict_to_node(data["root"])
        self.node_map = {}
        self._build_node_map(self.root)

        self.current_node = self._find_last_active_node()

    

    def _dict_to_node(self, data: dict[str, Any]) -> TreeNode:

        children = [self._dict_to_node(child) for child in data.get("children", [])]

        return TreeNode(
            id=data["id"],
            agent_name=data["agent_name"],
            message=data["message"],
            summary=data.get("summary", ""),  # Default to empty string for backward compatibility
            parent=data.get("parent"),
            children=children,
            is_active=data.get("is_active", True),
            branch_id=data.get("branch_id", "main"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )

    def _build_node_map(self, node: TreeNode) -> None:

        self.node_map[node.id] = node
        for child in node.children:
            self._build_node_map(child)

    def _find_last_active_node(self) -> TreeNode:

        # Find the last node in the current branch that is active

        if self.root is None:
            raise RuntimeError("Tree not initialized")

        node = self.root

        while True:
            active_children = [child for child in node.children if child.is_active]
            if not active_children:
                return node
            
            matching = [c for c in active_children if c.branch_id == self.current_branch_id]
            node = matching[0] if matching else active_children[-1]

    def find_node_by_id(self, node_id: str) -> TreeNode | None:
        return self.node_map.get(node_id)
    
    def get_active_branch_path(self) -> list[TreeNode]:

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
        if self.root is None:
            return {}
        
        branches: dict[str, list[TreeNode]] = {}

        def collect_branches(node: TreeNode) -> None:
            if node.branch_id not in branches:
                branches[node.branch_id] = []
            branches[node.branch_id].append(node)

            for child in node.children:
                collect_branches(self.root)
        
        collect_branches(self.root)
        return branches

    def get_subtree(self, node_id: str, max_depth: int | None = None) -> TreeNode | None:
        # Gets you the subtree starting from a specific node

        node = self.find_node_by_id(node_id)
        if node is None:
            return None

        if max_depth == 0:
            # Return node without children
            return TreeNode(
                id=node.id,
                agent_name=node.agent_name,
                message=node.message,
                summary=node.summary,
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
                    summary=n.summary,
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
                summary=n.summary,
                parent=n.parent,
                children=[limit_depth(child, depth - 1) for child in n.children],
                is_active=n.is_active,
                branch_id=n.branch_id,
                timestamp=n.timestamp,
            )

        return limit_depth(node, max_depth)
    
    def get_tree_depth(self) -> int:

        if self.root is None:
            raise RuntimeError("Tree not initialized")

        def calculate_depth(node: TreeNode) -> int:
            if not node.children:
                return 0
            return 1 + max(calculate_depth(child) for child in node.children)

        return calculate_depth(self.root)

    
    def get_tree_breadth(self) -> int:

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

        if self.current_node is None or self.root is None:
            raise RuntimeError("Tree not initialized")

        path = self.get_active_branch_path()
        return list(reversed(path[-count:]))

    def get_ancestors(self, node_id: str) -> list[TreeNode]:

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

        if self.root is None or self.current_node is None:
            raise RuntimeError("Tree not initialized")
        
         # Find center node (last user message if not specified)
        if center_node_id is None:
            # Find the last user message in the active branch
            path = self.get_active_branch_path()
            center = None
            for node in reversed(path):
                if node.agent_name.lower() in ["user", "usercontrol", "usercontrolagent"]: # TODO: unify and generalize the user messages that get routed through the UserControlAgent AND UserProxyAgent
                    center = node
                    break
            if center is None:
                center = self.current_node
        else:
            center = self.find_node_by_id(center_node_id)
            if center is None:
                raise ValueError(f"Center node {center_node_id} not found")

        visible_nodes: list[TreeNode] = [center]

        ancestors_to_add = max_height // 2
        current = center

        for _ in range(ancestors_to_add):
            if current.parent is None:
                break
            parent = self.node_map.get(current.parent)

            visible_nodes.append(parent)
            current = parent
        
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

    # TODO: look if this code is used somewhere if not delete it
    # def get_node_level(self, node_id: str) -> int:
        
    #     # Get the depth of the node in the tree (distance from root)

    #     node = self.find_node_by_id(node_id)
    #     if node is None:
    #         raise ValueError(f"Node with id {node_id} not found")

    #     level = 0
    #     current = node

    #     while current.parent is not None:
    #         level += 1
    #         parent = self.node_map.get(current.parent)
    #         if parent is None:
    #             break
    #         current = parent

    #     return level

    # def count_active_nodes(self) -> int:
    #     # Count the number of active nodes

    #     if self.root is None:
    #         raise RuntimeError("Tree not initialized")

    #     count = 0

    #     def traverse(node: TreeNode) -> None:
    #         nonlocal count
    #         if node.is_active:
    #             count += 1
    #         for child in node.children:
    #             traverse(child)

    #     traverse(self.root)
    #     return count

    # def count_total_nodes(self) -> int:

    #     if self.root is None:
    #         raise RuntimeError("Tree not initialized")

    #     return len(self.node_map)

    # def get_branch_point(self, node_id: str) -> TreeNode | None:
    #     node = self.find_node_by_id(node_id)
    #     if node is None:
    #         raise ValueError(f"Node with id {node_id} not found")

    #     current = node
    #     while current is not None:
    #         if len(current.children) > 1:
    #             return current
    #         if current.parent is None:
    #             return None
    #         current = self.node_map.get(current.parent)

    #     return None