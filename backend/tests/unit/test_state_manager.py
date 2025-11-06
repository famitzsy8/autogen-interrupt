"""Test StateManager tree operations"""

import pytest
from pathlib import Path
from handlers.state_manager import StateManager
from models import TreeNode


@pytest.fixture
def temp_state_file(tmp_path):
    return tmp_path / "test_state.json"


@pytest.fixture
def state_manager(temp_state_file):
    return StateManager(temp_state_file)


class TestStateManagerInitialization:
    def test_initialize_root(self, state_manager):
        root = state_manager.initialize_root("You", "Start conversation")

        assert state_manager.root is not None
        assert state_manager.root.agent_name == "You"
        assert state_manager.root.message == "Start conversation"
        assert state_manager.current_node == root
        assert root.id in state_manager.node_map

    def test_cannot_add_node_before_initialization(self, state_manager):
        with pytest.raises(RuntimeError, match="Tree not initialized"):
            state_manager.add_node("orchestrator", "Test message")

    def test_root_is_active(self, state_manager):
        root = state_manager.initialize_root("You", "Start")
        assert root.is_active is True

    def test_root_has_main_branch_id(self, state_manager):
        root = state_manager.initialize_root("You", "Start")
        assert root.branch_id == "main"

    def test_root_has_no_parent(self, state_manager):
        root = state_manager.initialize_root("You", "Start")
        assert root.parent is None


class TestStateManagerNodeOperations:
    def test_add_node(self, state_manager):
        state_manager.initialize_root("You", "Initial message")
        node = state_manager.add_node("orchestrator", "Response message")

        assert node is not None
        assert node.agent_name == "orchestrator"
        assert node.parent == state_manager.root.id
        assert node in state_manager.root.children
        assert state_manager.current_node == node

    def test_filter_gcm_messages(self, state_manager):
        """GroupChatManager messages should be filtered out"""
        state_manager.initialize_root("You", "Initial")
        gcm_node = state_manager.add_node("GroupChatManager", "GCM message")

        assert gcm_node is None
        assert state_manager.current_node == state_manager.root

    def test_sequential_nodes(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node1 = state_manager.add_node("orchestrator", "First")
        node2 = state_manager.add_node("bill_specialist", "Second")
        node3 = state_manager.add_node("orchestrator", "Third")

        assert node2.parent == node1.id
        assert node3.parent == node2.id
        assert state_manager.current_node == node3

    def test_node_added_to_parent_children(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node1 = state_manager.add_node("orchestrator", "First")

        assert len(state_manager.root.children) == 1
        assert state_manager.root.children[0] == node1

    def test_node_map_updated(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node = state_manager.add_node("orchestrator", "First")

        assert node.id in state_manager.node_map
        assert state_manager.node_map[node.id] == node

    def test_node_has_timestamp(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node = state_manager.add_node("orchestrator", "First")

        assert node.timestamp is not None


class TestStateManagerBranching:
    def test_create_branch_from_current(self, state_manager):
        state_manager.initialize_root("You", "Start")
        state_manager.add_node("orchestrator", "Message 1")
        state_manager.add_node("bill_specialist", "Message 2")

        # Branch from current (trim_count=0)
        branch_node = state_manager.create_branch(
            trim_count=0,
            user_message="User intervention"
        )

        assert branch_node.agent_name == "You"
        assert branch_node.message == "User intervention"
        assert state_manager.current_node == branch_node

    def test_create_branch_with_trim(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node1 = state_manager.add_node("orchestrator", "Message 1")
        node2 = state_manager.add_node("bill_specialist", "Message 2")

        # Branch from node1 (trim 1 message up)
        branch_node = state_manager.create_branch(
            trim_count=1,
            user_message="Branch from node1"
        )

        # The branch should be attached to node1
        assert branch_node.parent == node1.id
        # node2 should now be inactive
        assert node2.is_active is False

    def test_trim_count_exceeds_depth_raises_error(self, state_manager):
        state_manager.initialize_root("You", "Start")
        state_manager.add_node("orchestrator", "Message 1")

        with pytest.raises(RuntimeError, match="trim_count .* exceeds tree depth"):
            state_manager.create_branch(
                trim_count=10,
                user_message="Invalid branch"
            )

    def test_branch_creates_new_node_in_node_map(self, state_manager):
        state_manager.initialize_root("You", "Start")
        state_manager.add_node("orchestrator", "Message 1")

        original_count = len(state_manager.node_map)
        branch_node = state_manager.create_branch(
            trim_count=0,
            user_message="Branch"
        )

        assert len(state_manager.node_map) == original_count + 1
        assert branch_node.id in state_manager.node_map

    def test_multiple_branches_from_same_point(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node1 = state_manager.add_node("orchestrator", "Message 1")

        branch1 = state_manager.create_branch(trim_count=0, user_message="Branch 1")
        state_manager.current_node = node1  # Reset to node1
        branch2 = state_manager.create_branch(trim_count=0, user_message="Branch 2")

        assert len(node1.children) == 2
        assert branch1 in node1.children
        assert branch2 in node1.children


class TestStateManagerPersistence:
    def test_save_to_file(self, state_manager, temp_state_file):
        state_manager.initialize_root("You", "Start")
        state_manager.add_node("orchestrator", "Message 1")

        state_manager.save_to_file()
        assert temp_state_file.exists()

    def test_save_and_load(self, state_manager, temp_state_file):
        # Build a tree
        state_manager.initialize_root("You", "Start")
        state_manager.add_node("orchestrator", "Message 1")
        state_manager.add_node("bill_specialist", "Message 2")

        # Save
        state_manager.save_to_file()
        assert temp_state_file.exists()

        # Load into new manager
        new_manager = StateManager(temp_state_file)
        new_manager.load_from_file()

        assert new_manager.root.message == "Start"
        assert len(new_manager.node_map) == 3
        assert new_manager.current_node.message == "Message 2"

    def test_save_before_initialization_fails(self, state_manager):
        with pytest.raises(RuntimeError, match="Tree not initialized"):
            state_manager.save_to_file()

    def test_load_nonexistent_file_fails(self, tmp_path):
        manager = StateManager(tmp_path / "nonexistent.json")
        with pytest.raises(FileNotFoundError):
            manager.load_from_file()

    def test_save_creates_parent_directories(self, tmp_path):
        nested_path = tmp_path / "deep" / "nested" / "state.json"
        manager = StateManager(nested_path)
        manager.initialize_root("You", "Start")

        manager.save_to_file()
        assert nested_path.exists()

    def test_load_preserves_branch_structure(self, state_manager, temp_state_file):
        state_manager.initialize_root("You", "Start")
        node1 = state_manager.add_node("orchestrator", "Message 1")
        state_manager.create_branch(trim_count=0, user_message="Branch")

        state_manager.save_to_file()

        new_manager = StateManager(temp_state_file)
        new_manager.load_from_file()

        # Branching from current with trim_count=0 just continues the branch
        loaded_node1 = new_manager.find_node_by_id(node1.id)
        assert loaded_node1 is not None
        assert len(loaded_node1.children) == 1


class TestStateManagerQueries:
    def test_get_active_branch_path(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node1 = state_manager.add_node("orchestrator", "Msg1")
        node2 = state_manager.add_node("bill_specialist", "Msg2")

        path = state_manager.get_active_branch_path()

        assert len(path) == 3
        assert path[0] == state_manager.root
        assert path[1] == node1
        assert path[2] == node2

    def test_find_node_by_id(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node = state_manager.add_node("orchestrator", "Message")

        found = state_manager.find_node_by_id(node.id)
        assert found == node

        not_found = state_manager.find_node_by_id("nonexistent")
        assert not_found is None

    def test_get_tree_depth(self, state_manager):
        state_manager.initialize_root("You", "Start")
        assert state_manager.get_tree_depth() == 0

        state_manager.add_node("orchestrator", "Msg1")
        assert state_manager.get_tree_depth() == 1

        state_manager.add_node("bill_specialist", "Msg2")
        assert state_manager.get_tree_depth() == 2

    def test_get_tree_breadth(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node1 = state_manager.add_node("orchestrator", "Msg1")

        # Create two branches from node1
        state_manager.create_branch(trim_count=0, user_message="Branch1")
        state_manager.current_node = node1
        state_manager.create_branch(trim_count=0, user_message="Branch2")

        breadth = state_manager.get_tree_breadth()
        assert breadth == 2

    def test_get_ancestors(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node1 = state_manager.add_node("orchestrator", "Msg1")
        node2 = state_manager.add_node("bill_specialist", "Msg2")

        ancestors = state_manager.get_ancestors(node2.id)
        assert len(ancestors) == 2
        assert ancestors[0] == state_manager.root
        assert ancestors[1] == node1

    def test_get_descendants(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node1 = state_manager.add_node("orchestrator", "Msg1")
        node2 = state_manager.add_node("bill_specialist", "Msg2")

        descendants = state_manager.get_descendants(state_manager.root.id)
        assert len(descendants) == 2
        assert node1 in descendants
        assert node2 in descendants

    def test_get_siblings(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node1 = state_manager.add_node("orchestrator", "Msg1")

        # Create siblings
        branch1 = state_manager.create_branch(trim_count=0, user_message="Branch1")
        state_manager.current_node = node1
        branch2 = state_manager.create_branch(trim_count=0, user_message="Branch2")

        siblings = state_manager.get_siblings(branch1.id)
        assert len(siblings) == 1
        assert branch2 in siblings


class TestStateManagerReset:
    def test_reset(self, state_manager):
        state_manager.initialize_root("You", "Start")
        state_manager.add_node("orchestrator", "Message 1")

        assert state_manager.root is not None
        assert len(state_manager.node_map) > 0

        state_manager.reset()

        assert state_manager.root is None
        assert state_manager.current_node is None
        assert state_manager.current_branch_id == "main"
        assert len(state_manager.node_map) == 0


class TestStateManagerEdgeCases:
    def test_get_recent_nodes(self, state_manager):
        state_manager.initialize_root("You", "Start")
        state_manager.add_node("orchestrator", "Msg1")
        state_manager.add_node("bill_specialist", "Msg2")
        state_manager.add_node("committee_specialist", "Msg3")

        recent = state_manager.get_recent_nodes(2)
        assert len(recent) == 2
        # Should be in reverse order (most recent first)

    def test_get_subtree(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node1 = state_manager.add_node("orchestrator", "Msg1")
        state_manager.add_node("bill_specialist", "Msg2")

        subtree = state_manager.get_subtree(node1.id)
        assert subtree is not None
        assert subtree.id == node1.id

    def test_get_subtree_with_max_depth(self, state_manager):
        state_manager.initialize_root("You", "Start")
        node1 = state_manager.add_node("orchestrator", "Msg1")
        state_manager.add_node("bill_specialist", "Msg2")

        subtree = state_manager.get_subtree(node1.id, max_depth=0)
        assert subtree is not None
        assert len(subtree.children) == 0
