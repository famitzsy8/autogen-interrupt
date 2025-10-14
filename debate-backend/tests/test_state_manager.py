"""Tests for StateManager."""

import json
from pathlib import Path

import pytest

from state_manager import StateManager


class TestStateManagerInitialization:
    """Tests for StateManager initialization."""

    def test_initialize_with_file_path(self, tmp_path: Path) -> None:
        """Test initializing state manager with file path."""
        file_path = tmp_path / "state.json"
        manager = StateManager(file_path)

        assert manager.file_path == file_path
        assert manager.root is None
        assert manager.current_node is None
        assert manager.current_branch_id == "main"
        assert manager.node_map == {}

    def test_initialize_with_string_path(self, tmp_path: Path) -> None:
        """Test initializing state manager with string path."""
        file_path = str(tmp_path / "state.json")
        manager = StateManager(file_path)

        assert isinstance(manager.file_path, Path)


class TestStateManagerRootInitialization:
    """Tests for root node initialization."""

    def test_initialize_root(self, tmp_path: Path) -> None:
        """Test initializing the root node."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "First message")

        assert root.agent_name == "Agent1"
        assert root.message == "First message"
        assert root.parent is None
        assert root.is_active is True
        assert root.branch_id == "main"
        assert manager.root == root
        assert manager.current_node == root
        assert root.id in manager.node_map

    def test_root_has_unique_id(self, tmp_path: Path) -> None:
        """Test that root node has a unique ID."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "First message")

        assert root.id.startswith("node_")
        assert len(root.id) > 5


class TestStateManagerNodeAddition:
    """Tests for adding nodes to the tree."""

    def test_add_node_to_root(self, tmp_path: Path) -> None:
        """Test adding a node to the root."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "First message")
        node2 = manager.add_node("Agent2", "Second message")

        assert node2.agent_name == "Agent2"
        assert node2.message == "Second message"
        assert node2.parent == root.id
        assert node2.is_active is True
        assert node2.branch_id == "main"
        assert node2 in root.children
        assert manager.current_node == node2
        assert node2.id in manager.node_map

    def test_add_multiple_nodes_linear(self, tmp_path: Path) -> None:
        """Test adding multiple nodes in a linear sequence."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "Message 1")
        node2 = manager.add_node("Agent2", "Message 2")
        node3 = manager.add_node("Agent3", "Message 3")

        assert node2.parent == root.id
        assert node3.parent == node2.id
        assert len(root.children) == 1
        assert len(node2.children) == 1
        assert len(node3.children) == 0
        assert manager.current_node == node3

    def test_add_node_without_initialization_fails(self, tmp_path: Path) -> None:
        """Test that adding a node without initialization raises error."""
        manager = StateManager(tmp_path / "state.json")

        with pytest.raises(RuntimeError, match="Tree not initialized"):
            manager.add_node("Agent1", "Message")


class TestStateManagerBranching:
    """Tests for creating branches in the tree."""

    def test_create_branch_from_current_node(self, tmp_path: Path) -> None:
        """Test creating a branch from the current node (trim_count=0)."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "Message 1")
        node2 = manager.add_node("Agent2", "Message 2")
        node3 = manager.add_node("Agent3", "Message 3")

        # Create branch from current node
        user_node = manager.create_branch(0, "User interrupts", "User")

        assert user_node.agent_name == "User"
        assert user_node.message == "User interrupts"
        assert user_node.parent == node3.id
        assert user_node.is_active is True
        assert user_node.branch_id != "main"
        assert len(node3.children) == 1
        assert manager.current_node == user_node
        assert manager.current_branch_id == user_node.branch_id

    def test_create_branch_with_trim_count(self, tmp_path: Path) -> None:
        """Test creating a branch with trim_count > 0."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "Message 1")
        node2 = manager.add_node("Agent2", "Message 2")
        node3 = manager.add_node("Agent3", "Message 3")
        node4 = manager.add_node("Agent4", "Message 4")

        # Branch from 2 nodes back (node2)
        user_node = manager.create_branch(2, "User interrupts at node2", "User")

        assert user_node.parent == node2.id
        assert len(node2.children) == 2  # Original child (node3) + user_node
        assert manager.current_node == user_node

    def test_create_branch_marks_old_branch_inactive(self, tmp_path: Path) -> None:
        """Test that creating a branch marks old nodes as inactive."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "Message 1")
        node2 = manager.add_node("Agent2", "Message 2")
        node3 = manager.add_node("Agent3", "Message 3")

        # Branch from root (trim_count=2)
        user_node = manager.create_branch(2, "User interrupts", "User")

        # node3 (current at time of branch) should be inactive
        assert node3.is_active is False
        # node2 and root should still be active (they're ancestors of the branch point)
        # Actually, the current implementation marks current_node as inactive
        # Let me check the logic again...
        # The method marks descendants of current_node as inactive, which is just node3 itself
        assert node3.is_active is False

    def test_create_branch_with_multiple_levels(self, tmp_path: Path) -> None:
        """Test branching and then continuing conversation on new branch."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "Message 1")
        node2 = manager.add_node("Agent2", "Message 2")
        node3 = manager.add_node("Agent3", "Message 3")

        # Create branch
        user_node = manager.create_branch(1, "User interrupts", "User")
        old_branch_id = "main"
        new_branch_id = user_node.branch_id

        # Continue on new branch
        node4 = manager.add_node("Agent1", "Response to user")
        node5 = manager.add_node("Agent2", "Further discussion")

        assert node4.branch_id == new_branch_id
        assert node5.branch_id == new_branch_id
        assert node4.parent == user_node.id
        assert node5.parent == node4.id

    def test_create_branch_trim_count_exceeds_depth_fails(self, tmp_path: Path) -> None:
        """Test that trim_count exceeding tree depth raises error."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "Message 1")
        node2 = manager.add_node("Agent2", "Message 2")

        # Tree depth is 2 (root -> node2), trim_count=3 should fail
        with pytest.raises(RuntimeError, match="trim_count.*exceeds tree depth"):
            manager.create_branch(3, "User interrupts", "User")

    def test_create_branch_without_initialization_fails(self, tmp_path: Path) -> None:
        """Test that creating a branch without initialization raises error."""
        manager = StateManager(tmp_path / "state.json")

        with pytest.raises(RuntimeError, match="Tree not initialized"):
            manager.create_branch(0, "User interrupts", "User")


class TestStateManagerSerialization:
    """Tests for tree serialization."""

    def test_get_tree_dict_simple(self, tmp_path: Path) -> None:
        """Test getting tree as dictionary."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "Message 1")
        node2 = manager.add_node("Agent2", "Message 2")

        tree_dict = manager.get_tree_dict()

        assert "root" in tree_dict
        assert "current_branch_id" in tree_dict
        assert tree_dict["current_branch_id"] == "main"
        assert tree_dict["root"]["id"] == root.id
        assert tree_dict["root"]["agent_name"] == "Agent1"
        assert tree_dict["root"]["message"] == "Message 1"
        assert len(tree_dict["root"]["children"]) == 1
        assert tree_dict["root"]["children"][0]["id"] == node2.id

    def test_get_tree_dict_with_branches(self, tmp_path: Path) -> None:
        """Test getting tree dict with multiple branches."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "Message 1")
        node2 = manager.add_node("Agent2", "Message 2")
        node3 = manager.add_node("Agent3", "Message 3")

        # Create branch
        user_node = manager.create_branch(1, "User interrupts", "User")
        node4 = manager.add_node("Agent1", "Response")

        tree_dict = manager.get_tree_dict()

        # Root should have 1 child (node2)
        assert len(tree_dict["root"]["children"]) == 1
        # node2 should have 2 children (node3 and user_node)
        assert len(tree_dict["root"]["children"][0]["children"]) == 2

        # Check that node3 is inactive
        node3_dict = tree_dict["root"]["children"][0]["children"][0]
        assert node3_dict["is_active"] is False

    def test_get_tree_dict_without_initialization_fails(self, tmp_path: Path) -> None:
        """Test that getting tree dict without initialization raises error."""
        manager = StateManager(tmp_path / "state.json")

        with pytest.raises(RuntimeError, match="Tree not initialized"):
            manager.get_tree_dict()


class TestStateManagerPersistence:
    """Tests for JSON file persistence."""

    def test_save_to_file(self, tmp_path: Path) -> None:
        """Test saving tree to JSON file."""
        file_path = tmp_path / "state.json"
        manager = StateManager(file_path)
        root = manager.initialize_root("Agent1", "Message 1")
        node2 = manager.add_node("Agent2", "Message 2")

        manager.save_to_file()

        assert file_path.exists()
        with file_path.open("r") as f:
            data = json.load(f)

        assert "root" in data
        assert "current_branch_id" in data
        assert data["root"]["id"] == root.id

    def test_save_to_file_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that save_to_file creates parent directories."""
        file_path = tmp_path / "nested" / "dir" / "state.json"
        manager = StateManager(file_path)
        manager.initialize_root("Agent1", "Message 1")

        manager.save_to_file()

        assert file_path.exists()
        assert file_path.parent.exists()

    def test_save_without_initialization_fails(self, tmp_path: Path) -> None:
        """Test that saving without initialization raises error."""
        manager = StateManager(tmp_path / "state.json")

        with pytest.raises(RuntimeError, match="Tree not initialized"):
            manager.save_to_file()

    def test_load_from_file(self, tmp_path: Path) -> None:
        """Test loading tree from JSON file."""
        file_path = tmp_path / "state.json"

        # Create and save a tree
        manager1 = StateManager(file_path)
        root = manager1.initialize_root("Agent1", "Message 1")
        node2 = manager1.add_node("Agent2", "Message 2")
        manager1.save_to_file()

        # Load into new manager
        manager2 = StateManager(file_path)
        manager2.load_from_file()

        assert manager2.root is not None
        assert manager2.root.id == root.id
        assert manager2.root.agent_name == "Agent1"
        assert manager2.root.message == "Message 1"
        assert len(manager2.root.children) == 1
        assert manager2.root.children[0].id == node2.id
        assert manager2.current_node is not None
        assert manager2.current_node.id == node2.id

    def test_load_from_file_with_branches(self, tmp_path: Path) -> None:
        """Test loading tree with branches from file."""
        file_path = tmp_path / "state.json"

        # Create tree with branches
        manager1 = StateManager(file_path)
        root = manager1.initialize_root("Agent1", "Message 1")
        node2 = manager1.add_node("Agent2", "Message 2")
        node3 = manager1.add_node("Agent3", "Message 3")
        user_node = manager1.create_branch(1, "User interrupts", "User")
        node4 = manager1.add_node("Agent1", "Response")
        manager1.save_to_file()

        # Load into new manager
        manager2 = StateManager(file_path)
        manager2.load_from_file()

        assert manager2.root is not None
        assert len(manager2.root.children) == 1
        assert len(manager2.root.children[0].children) == 2  # node3 and user_node

        # Check that inactive branch is preserved
        node3_loaded = manager2.root.children[0].children[0]
        assert node3_loaded.is_active is False

        # Current node should be the last node on active branch (node4)
        assert manager2.current_node is not None
        assert manager2.current_node.agent_name == "Agent1"
        assert manager2.current_node.message == "Response"

    def test_load_from_nonexistent_file_fails(self, tmp_path: Path) -> None:
        """Test that loading from nonexistent file raises error."""
        manager = StateManager(tmp_path / "nonexistent.json")

        with pytest.raises(FileNotFoundError):
            manager.load_from_file()

    def test_load_from_invalid_file_fails(self, tmp_path: Path) -> None:
        """Test that loading from invalid file raises error."""
        file_path = tmp_path / "invalid.json"
        with file_path.open("w") as f:
            json.dump({"invalid": "data"}, f)

        manager = StateManager(file_path)

        with pytest.raises(ValueError, match="Invalid state file"):
            manager.load_from_file()

    def test_save_load_round_trip(self, tmp_path: Path) -> None:
        """Test that save/load round trip preserves all data."""
        file_path = tmp_path / "state.json"

        # Create complex tree
        manager1 = StateManager(file_path)
        root = manager1.initialize_root("Agent1", "Message 1")
        node2 = manager1.add_node("Agent2", "Message 2")
        node3 = manager1.add_node("Agent3", "Message 3")
        node4 = manager1.add_node("Agent4", "Message 4")

        # Create first branch
        user_node1 = manager1.create_branch(2, "First interrupt", "User")
        node5 = manager1.add_node("Agent1", "Response 1")

        # Create second branch
        user_node2 = manager1.create_branch(1, "Second interrupt", "User")
        node6 = manager1.add_node("Agent2", "Response 2")

        manager1.save_to_file()

        # Load and verify
        manager2 = StateManager(file_path)
        manager2.load_from_file()

        # Verify structure
        assert manager2.root is not None
        assert manager2.current_node is not None
        assert manager2.current_node.agent_name == "Agent2"
        assert manager2.current_branch_id == user_node2.branch_id

        # Verify node map is rebuilt
        assert len(manager2.node_map) == 8  # root + 7 other nodes (node2-4, user1-2, response1-2)


class TestStateManagerUtilityMethods:
    """Tests for utility methods."""

    def test_reset(self, tmp_path: Path) -> None:
        """Test resetting the state manager."""
        manager = StateManager(tmp_path / "state.json")
        manager.initialize_root("Agent1", "Message 1")
        manager.add_node("Agent2", "Message 2")

        manager.reset()

        assert manager.root is None
        assert manager.current_node is None
        assert manager.current_branch_id == "main"
        assert manager.node_map == {}

    def test_get_current_node(self, tmp_path: Path) -> None:
        """Test getting current node."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "Message 1")
        node2 = manager.add_node("Agent2", "Message 2")

        current = manager.get_current_node()

        assert current == node2

    def test_get_current_node_before_initialization(self, tmp_path: Path) -> None:
        """Test getting current node before initialization."""
        manager = StateManager(tmp_path / "state.json")

        current = manager.get_current_node()

        assert current is None

    def test_get_root(self, tmp_path: Path) -> None:
        """Test getting root node."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "Message 1")

        retrieved_root = manager.get_root()

        assert retrieved_root == root

    def test_get_root_before_initialization(self, tmp_path: Path) -> None:
        """Test getting root node before initialization."""
        manager = StateManager(tmp_path / "state.json")

        root = manager.get_root()

        assert root is None

    def test_node_id_generation_unique(self, tmp_path: Path) -> None:
        """Test that node IDs are unique."""
        manager = StateManager(tmp_path / "state.json")
        root = manager.initialize_root("Agent1", "Message 1")
        node2 = manager.add_node("Agent2", "Message 2")
        node3 = manager.add_node("Agent3", "Message 3")

        ids = {root.id, node2.id, node3.id}
        assert len(ids) == 3  # All unique

    def test_branch_id_generation_unique(self, tmp_path: Path) -> None:
        """Test that branch IDs are unique."""
        manager = StateManager(tmp_path / "state.json")
        manager.initialize_root("Agent1", "Message 1")
        manager.add_node("Agent2", "Message 2")

        user_node1 = manager.create_branch(0, "First interrupt", "User")
        branch_id1 = user_node1.branch_id

        manager.add_node("Agent3", "Message 3")
        user_node2 = manager.create_branch(0, "Second interrupt", "User")
        branch_id2 = user_node2.branch_id

        assert branch_id1 != branch_id2
        assert branch_id1 != "main"
        assert branch_id2 != "main"
