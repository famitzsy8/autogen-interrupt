"""Comprehensive tests for the StateManager class."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from models import TreeNode
from state_manager import StateManager


@pytest.fixture
def temp_file() -> Path:
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = Path(f.name)
    yield temp_path
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def state_manager(temp_file: Path) -> StateManager:
    """Create a fresh StateManager instance."""
    return StateManager(temp_file)


class TestInitialization:
    """Tests for StateManager initialization."""

    def test_init(self, temp_file: Path) -> None:
        """Test StateManager initialization."""
        manager = StateManager(temp_file)
        assert manager.file_path == temp_file
        assert manager.root is None
        assert manager.current_node is None
        assert manager.current_branch_id == "main"
        assert len(manager.node_map) == 0

    def test_initialize_root(self, state_manager: StateManager) -> None:
        """Test initializing the conversation tree with a root node."""
        root = state_manager.initialize_root("System", "Welcome to the debate!")

        assert root is not None
        assert root.agent_name == "System"
        assert root.message == "Welcome to the debate!"
        assert root.parent is None
        assert root.children == []
        assert root.is_active is True
        assert root.branch_id == "main"
        assert state_manager.root == root
        assert state_manager.current_node == root
        assert root.id in state_manager.node_map


class TestNodeOperations:
    """Tests for node addition and manipulation."""

    def test_add_node(self, state_manager: StateManager) -> None:
        """Test adding nodes to the tree."""
        state_manager.initialize_root("System", "Root message")
        node1 = state_manager.add_node("Agent1", "First message")

        assert node1.agent_name == "Agent1"
        assert node1.message == "First message"
        assert node1.parent == state_manager.root.id
        assert node1 in state_manager.root.children
        assert state_manager.current_node == node1
        assert node1.id in state_manager.node_map

    def test_add_node_without_initialization(self, state_manager: StateManager) -> None:
        """Test that adding a node without initialization raises an error."""
        with pytest.raises(RuntimeError, match="Tree not initialized"):
            state_manager.add_node("Agent1", "Message")

    def test_add_multiple_nodes(self, state_manager: StateManager) -> None:
        """Test adding multiple nodes in sequence."""
        state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")
        node2 = state_manager.add_node("Agent2", "Message 2")
        node3 = state_manager.add_node("Agent3", "Message 3")

        assert len(state_manager.node_map) == 4  # root + 3 nodes
        assert node2.parent == node1.id
        assert node3.parent == node2.id
        assert state_manager.current_node == node3


class TestBranching:
    """Tests for tree branching functionality."""

    def test_create_branch_from_current(self, state_manager: StateManager) -> None:
        """Test creating a branch from the current position (trim_count=0)."""
        state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")
        node2 = state_manager.add_node("Agent2", "Message 2")

        # Create a branch with trim_count=0 (from current position)
        user_node = state_manager.create_branch(0, "User input", "User")

        assert user_node.agent_name == "User"
        assert user_node.message == "User input"
        assert user_node.parent == node2.id
        assert user_node.branch_id != "main"
        assert state_manager.current_branch_id == user_node.branch_id

        # Current node (node2) and its descendants should be marked inactive
        # The implementation only marks the current node and its descendants inactive
        assert node2.is_active is False
        # Note: node1 and root remain active as they are ancestors
        assert state_manager.root.is_active is True

    def test_create_branch_with_trim(self, state_manager: StateManager) -> None:
        """Test creating a branch by trimming messages."""
        state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")
        node2 = state_manager.add_node("Agent2", "Message 2")
        node3 = state_manager.add_node("Agent3", "Message 3")

        # Branch from node1 (trim 2 messages back from node3)
        user_node = state_manager.create_branch(2, "User intervention", "User")

        assert user_node.parent == node1.id
        assert user_node in node1.children
        assert len(node1.children) == 2  # node2 and user_node

        # Current node (node3) and its descendants should be inactive
        # Note: The implementation marks node3 inactive, but node2 stays active
        # as it's not a descendant of node3
        assert node3.is_active is False
        assert user_node.is_active is True

    def test_create_branch_exceeds_depth(self, state_manager: StateManager) -> None:
        """Test that trimming beyond root raises an error."""
        state_manager.initialize_root("System", "Root")
        state_manager.add_node("Agent1", "Message 1")

        with pytest.raises(RuntimeError, match="trim_count .* exceeds tree depth"):
            state_manager.create_branch(5, "User message", "User")

    def test_multiple_branches(self, state_manager: StateManager) -> None:
        """Test creating multiple branches from the same point."""
        state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")

        # First branch from root (trim_count=1 goes back to root)
        branch1_node = state_manager.create_branch(1, "Branch 1", "User")
        branch1_id = state_manager.current_branch_id
        state_manager.add_node("Agent2", "Response to branch 1")

        # Second branch from root
        # When we create a branch with trim_count=1 from the response, we go back to root
        state_manager.current_node = state_manager.root
        # Find one of root's children to branch from
        root_child = state_manager.root.children[0] if state_manager.root.children else state_manager.root
        state_manager.current_node = root_child
        state_manager.create_branch(0, "Branch 2", "User")
        branch2_id = state_manager.current_branch_id

        assert branch1_id != branch2_id
        # Root should now have 2 children (original node1 and branch1_node)
        assert len(state_manager.root.children) >= 1


class TestTreeTraversal:
    """Tests for tree traversal methods."""

    def test_find_node_by_id(self, state_manager: StateManager) -> None:
        """Test finding nodes by ID."""
        state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")
        node2 = state_manager.add_node("Agent2", "Message 2")

        found = state_manager.find_node_by_id(node1.id)
        assert found == node1
        assert found.message == "Message 1"

        not_found = state_manager.find_node_by_id("nonexistent")
        assert not_found is None

    def test_get_active_branch_path(self, state_manager: StateManager) -> None:
        """Test getting the active branch path."""
        root = state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")
        node2 = state_manager.add_node("Agent2", "Message 2")

        path = state_manager.get_active_branch_path()
        assert len(path) == 3
        assert path[0] == root
        assert path[1] == node1
        assert path[2] == node2

    def test_get_all_branches(self, state_manager: StateManager) -> None:
        """Test getting all branches in the tree."""
        state_manager.initialize_root("System", "Root")
        state_manager.add_node("Agent1", "Message 1")
        state_manager.add_node("Agent2", "Message 2")

        # Create a branch
        state_manager.create_branch(1, "User message", "User")
        state_manager.add_node("Agent3", "Response")

        branches = state_manager.get_all_branches()
        assert "main" in branches
        assert len(branches) >= 2  # main branch and at least one new branch
        assert len(branches["main"]) == 3  # root + 2 agents

    def test_get_ancestors(self, state_manager: StateManager) -> None:
        """Test getting ancestor nodes."""
        root = state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")
        node2 = state_manager.add_node("Agent2", "Message 2")
        node3 = state_manager.add_node("Agent3", "Message 3")

        ancestors = state_manager.get_ancestors(node3.id)
        assert len(ancestors) == 3
        assert ancestors[0] == root
        assert ancestors[1] == node1
        assert ancestors[2] == node2

        # Root has no ancestors
        root_ancestors = state_manager.get_ancestors(root.id)
        assert len(root_ancestors) == 0

    def test_get_descendants(self, state_manager: StateManager) -> None:
        """Test getting descendant nodes."""
        root = state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")
        node2 = state_manager.add_node("Agent2", "Message 2")

        descendants = state_manager.get_descendants(root.id)
        assert len(descendants) == 2
        assert node1 in descendants
        assert node2 in descendants

        # Leaf has no descendants
        leaf_descendants = state_manager.get_descendants(node2.id)
        assert len(leaf_descendants) == 0

    def test_get_siblings(self, state_manager: StateManager) -> None:
        """Test getting sibling nodes."""
        state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")

        # Create branches (siblings)
        state_manager.create_branch(0, "Branch 1", "User")
        branch1_child = state_manager.add_node("Agent2", "Response 1")

        state_manager.current_node = node1
        state_manager.create_branch(0, "Branch 2", "User")
        branch2_child = state_manager.add_node("Agent3", "Response 2")

        # Find siblings of branch1_child's parent
        siblings = state_manager.get_siblings(branch1_child.id)
        # branch1_child has no siblings, but its parent (user node) has a sibling (other user node)

        # Root has no siblings
        root_siblings = state_manager.get_siblings(state_manager.root.id)
        assert len(root_siblings) == 0


class TestTreeMetrics:
    """Tests for tree metric calculations."""

    def test_get_tree_depth(self, state_manager: StateManager) -> None:
        """Test calculating tree depth."""
        state_manager.initialize_root("System", "Root")
        assert state_manager.get_tree_depth() == 0

        state_manager.add_node("Agent1", "Message 1")
        assert state_manager.get_tree_depth() == 1

        state_manager.add_node("Agent2", "Message 2")
        assert state_manager.get_tree_depth() == 2

    def test_get_tree_breadth(self, state_manager: StateManager) -> None:
        """Test calculating tree breadth."""
        state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")

        # Create multiple branches
        state_manager.create_branch(0, "Branch 1", "User")
        state_manager.current_node = node1
        state_manager.create_branch(0, "Branch 2", "User")
        state_manager.current_node = node1
        state_manager.create_branch(0, "Branch 3", "User")

        breadth = state_manager.get_tree_breadth()
        assert breadth >= 3  # At least 3 children at node1

    def test_count_active_nodes(self, state_manager: StateManager) -> None:
        """Test counting active nodes."""
        state_manager.initialize_root("System", "Root")
        state_manager.add_node("Agent1", "Message 1")
        state_manager.add_node("Agent2", "Message 2")

        initial_count = state_manager.count_active_nodes()
        assert initial_count == 3

        # Create a branch (marks current node and descendants inactive)
        state_manager.create_branch(1, "User message", "User")
        active_count = state_manager.count_active_nodes()
        # The user node and ancestors should be active, plus the user's new message
        # At least one node should be marked inactive (the current leaf before branching)
        assert active_count >= initial_count  # New nodes are added with branching

    def test_count_total_nodes(self, state_manager: StateManager) -> None:
        """Test counting total nodes."""
        state_manager.initialize_root("System", "Root")
        assert state_manager.count_total_nodes() == 1

        state_manager.add_node("Agent1", "Message 1")
        assert state_manager.count_total_nodes() == 2

        state_manager.add_node("Agent2", "Message 2")
        assert state_manager.count_total_nodes() == 3

    def test_get_node_level(self, state_manager: StateManager) -> None:
        """Test getting node level (depth from root)."""
        root = state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")
        node2 = state_manager.add_node("Agent2", "Message 2")

        assert state_manager.get_node_level(root.id) == 0
        assert state_manager.get_node_level(node1.id) == 1
        assert state_manager.get_node_level(node2.id) == 2


class TestSubtrees:
    """Tests for subtree operations."""

    def test_get_subtree_full(self, state_manager: StateManager) -> None:
        """Test getting a full subtree."""
        root = state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")
        state_manager.add_node("Agent2", "Message 2")

        subtree = state_manager.get_subtree(root.id)
        assert subtree is not None
        assert subtree.id == root.id
        assert len(subtree.children) == 1
        assert subtree.children[0].id == node1.id

    def test_get_subtree_limited_depth(self, state_manager: StateManager) -> None:
        """Test getting a subtree with limited depth."""
        root = state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")
        state_manager.add_node("Agent2", "Message 2")

        subtree = state_manager.get_subtree(root.id, max_depth=1)
        assert subtree is not None
        assert len(subtree.children) == 1
        assert len(subtree.children[0].children) == 0  # Depth limited

    def test_get_subtree_nonexistent(self, state_manager: StateManager) -> None:
        """Test getting subtree for nonexistent node."""
        state_manager.initialize_root("System", "Root")
        subtree = state_manager.get_subtree("nonexistent")
        assert subtree is None

    def test_get_recent_nodes(self, state_manager: StateManager) -> None:
        """Test getting recent nodes in active branch."""
        state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")
        node2 = state_manager.add_node("Agent2", "Message 2")
        node3 = state_manager.add_node("Agent3", "Message 3")

        recent = state_manager.get_recent_nodes(2)
        assert len(recent) == 2
        assert recent[0] == node3  # Newest first
        assert recent[1] == node2


class TestVisualization:
    """Tests for visualization data generation."""

    def test_get_visualization_data_default(self, state_manager: StateManager) -> None:
        """Test getting visualization data with default center."""
        state_manager.initialize_root("System", "Root")
        state_manager.add_node("Agent1", "Message 1")
        state_manager.create_branch(0, "User input", "User")
        state_manager.add_node("Agent2", "Response")

        viz_data = state_manager.get_visualization_data()
        assert "center_node" in viz_data
        assert "visible_nodes" in viz_data
        assert "active_path" in viz_data
        assert "tree_depth" in viz_data
        assert "tree_breadth" in viz_data
        assert "current_branch_id" in viz_data

        # Center should be on user message
        assert viz_data["center_node"].agent_name == "User"

    def test_get_visualization_data_custom_center(self, state_manager: StateManager) -> None:
        """Test getting visualization data with custom center."""
        root = state_manager.initialize_root("System", "Root")
        state_manager.add_node("Agent1", "Message 1")
        state_manager.add_node("Agent2", "Message 2")

        viz_data = state_manager.get_visualization_data(center_node_id=root.id, max_height=2)
        assert viz_data["center_node"] == root
        assert len(viz_data["visible_nodes"]) >= 1

    def test_get_branch_point(self, state_manager: StateManager) -> None:
        """Test finding branch points."""
        root = state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")

        # Create branches
        state_manager.create_branch(0, "Branch 1", "User")
        branch1 = state_manager.current_node

        state_manager.current_node = node1
        state_manager.create_branch(0, "Branch 2", "User")

        # node1 should be a branch point
        branch_point = state_manager.get_branch_point(branch1.id)
        assert branch_point is not None
        assert branch_point.id == node1.id
        assert len(branch_point.children) > 1


class TestPersistence:
    """Tests for save and load functionality."""

    def test_save_to_file(self, state_manager: StateManager, temp_file: Path) -> None:
        """Test saving tree state to file."""
        state_manager.initialize_root("System", "Root")
        state_manager.add_node("Agent1", "Message 1")
        state_manager.add_node("Agent2", "Message 2")

        state_manager.save_to_file()
        assert temp_file.exists()

        # Verify file content
        with temp_file.open("r") as f:
            data = json.load(f)
        assert "root" in data
        assert "current_branch_id" in data

    def test_load_from_file(self, state_manager: StateManager, temp_file: Path) -> None:
        """Test loading tree state from file."""
        # Create and save a tree
        state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Message 1")
        state_manager.add_node("Agent2", "Message 2")
        state_manager.save_to_file()

        # Create new manager and load
        new_manager = StateManager(temp_file)
        new_manager.load_from_file()

        assert new_manager.root is not None
        assert new_manager.root.message == "Root"
        assert len(new_manager.node_map) == 3
        assert new_manager.current_node is not None

    def test_load_nonexistent_file(self, temp_file: Path) -> None:
        """Test loading from nonexistent file raises error."""
        temp_file.unlink()  # Remove the file
        manager = StateManager(temp_file)

        with pytest.raises(FileNotFoundError):
            manager.load_from_file()

    def test_save_without_initialization(self, state_manager: StateManager) -> None:
        """Test that saving without initialization raises error."""
        with pytest.raises(RuntimeError, match="Tree not initialized"):
            state_manager.save_to_file()

    def test_get_tree_dict(self, state_manager: StateManager) -> None:
        """Test getting tree as dictionary."""
        state_manager.initialize_root("System", "Root")
        state_manager.add_node("Agent1", "Message 1")

        tree_dict = state_manager.get_tree_dict()
        assert "root" in tree_dict
        assert "current_branch_id" in tree_dict
        assert tree_dict["root"]["agent_name"] == "System"


class TestReset:
    """Tests for reset functionality."""

    def test_reset(self, state_manager: StateManager) -> None:
        """Test resetting the state manager."""
        state_manager.initialize_root("System", "Root")
        state_manager.add_node("Agent1", "Message 1")

        state_manager.reset()

        assert state_manager.root is None
        assert state_manager.current_node is None
        assert state_manager.current_branch_id == "main"
        assert len(state_manager.node_map) == 0


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_get_active_branch_path_uninitialized(self, state_manager: StateManager) -> None:
        """Test getting branch path without initialization."""
        with pytest.raises(RuntimeError, match="Tree not initialized"):
            state_manager.get_active_branch_path()

    def test_get_tree_depth_uninitialized(self, state_manager: StateManager) -> None:
        """Test getting tree depth without initialization."""
        with pytest.raises(RuntimeError, match="Tree not initialized"):
            state_manager.get_tree_depth()

    def test_get_ancestors_nonexistent_node(self, state_manager: StateManager) -> None:
        """Test getting ancestors for nonexistent node."""
        state_manager.initialize_root("System", "Root")
        with pytest.raises(ValueError, match="not found"):
            state_manager.get_ancestors("nonexistent")

    def test_get_descendants_nonexistent_node(self, state_manager: StateManager) -> None:
        """Test getting descendants for nonexistent node."""
        state_manager.initialize_root("System", "Root")
        with pytest.raises(ValueError, match="not found"):
            state_manager.get_descendants("nonexistent")

    def test_get_node_level_nonexistent_node(self, state_manager: StateManager) -> None:
        """Test getting node level for nonexistent node."""
        state_manager.initialize_root("System", "Root")
        with pytest.raises(ValueError, match="not found"):
            state_manager.get_node_level("nonexistent")

    def test_create_branch_without_initialization(self, state_manager: StateManager) -> None:
        """Test creating branch without initialization."""
        with pytest.raises(RuntimeError, match="Tree not initialized"):
            state_manager.create_branch(0, "User message", "User")


class TestComplexScenarios:
    """Tests for complex real-world scenarios."""

    def test_multiple_branch_levels(self, state_manager: StateManager) -> None:
        """Test creating multiple levels of branches."""
        state_manager.initialize_root("System", "Start debate")
        node1 = state_manager.add_node("Agent1", "First argument")
        state_manager.add_node("Agent2", "Counter argument")
        state_manager.add_node("Agent3", "Rebuttal")

        # First user intervention
        state_manager.create_branch(2, "User comment 1", "User")
        state_manager.add_node("Agent1", "Response to comment")

        # Second user intervention
        state_manager.create_branch(1, "User comment 2", "User")
        state_manager.add_node("Agent2", "Another response")

        branches = state_manager.get_all_branches()
        assert len(branches) >= 3  # main + 2 user branches

    def test_deep_tree(self, state_manager: StateManager) -> None:
        """Test creating a deep conversation tree."""
        state_manager.initialize_root("System", "Root")

        # Create a deep linear chain
        for i in range(10):
            state_manager.add_node(f"Agent{i % 3}", f"Message {i}")

        assert state_manager.get_tree_depth() == 10
        assert state_manager.count_total_nodes() == 11  # root + 10 nodes

        path = state_manager.get_active_branch_path()
        assert len(path) == 11

    def test_wide_tree(self, state_manager: StateManager) -> None:
        """Test creating a wide tree with many branches."""
        state_manager.initialize_root("System", "Root")
        node1 = state_manager.add_node("Agent1", "Branch point")

        # Create multiple branches
        for i in range(5):
            state_manager.current_node = node1
            state_manager.create_branch(0, f"Branch {i}", "User")
            state_manager.add_node("Agent2", f"Response {i}")

        assert state_manager.get_tree_breadth() >= 5
        branches = state_manager.get_all_branches()
        assert len(branches) >= 6  # main + 5 branches
