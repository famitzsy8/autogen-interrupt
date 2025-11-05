"""Test agent team initialization from YAML"""

import pytest
import os
from factory.team_factory import init_team, load_data, AgentTeamContext
from handlers.agent_input_queue import AgentInputQueue


@pytest.fixture
def api_key():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set")
    return key


@pytest.fixture
def mock_input_queue():
    return AgentInputQueue()


class TestYAMLLoading:
    def test_load_team_yaml(self):
        """Test that team.yaml loads correctly"""
        data = load_data()

        assert "agents" in data
        assert "team" in data
        assert "llm" in data
        assert "tasks" in data

        # Check expected agents exist (now in dict keys)
        agent_names = list(data["agents"].keys())
        assert "orchestrator" in agent_names
        assert "bill_specialist" in agent_names
        assert "committee_specialist" in agent_names

    def test_yaml_agent_structure(self):
        """Validate agent configuration structure"""
        data = load_data()

        for agent_name, agent in data["agents"].items():
            assert "name" in agent
            assert "description" in agent
            assert "agent_class" in agent
            assert "system_message" in agent

            # Tools are optional but if present should have correct structure
            if "tools" in agent:
                assert "workbench_class" in agent["tools"]
                assert "allowed_tool_names" in agent["tools"]
                assert isinstance(agent["tools"]["allowed_tool_names"], list)

    def test_yaml_team_structure(self):
        """Validate team configuration structure"""
        data = load_data()
        team = data["team"]

        assert "group_chat_class" in team
        assert "group_chat_args" in team

        gc_args = team["group_chat_args"]
        assert "has_user_proxy" in gc_args
        assert "max_turns" in gc_args

    def test_yaml_llm_structure(self):
        """Validate LLM configuration structure"""
        data = load_data()
        llm = data["llm"]

        assert "model_client_class" in llm
        assert "model_client_args" in llm
        assert "model" in llm["model_client_args"]

    def test_yaml_agent_descriptions_not_empty(self):
        """All agents should have non-empty descriptions"""
        data = load_data()

        for agent_name, agent in data["agents"].items():
            assert agent["description"].strip() != "", \
                f"Agent {agent_name} has empty description"

    def test_yaml_agent_names_valid(self):
        """Agent names should be valid identifiers"""
        data = load_data()

        for agent_name, agent in data["agents"].items():
            name = agent["name"]
            # Should not be empty and should not have spaces
            assert name.strip() != ""
            assert " " not in name


class TestTeamInitialization:
    @pytest.mark.asyncio
    async def test_init_team_basic(self, api_key, mock_input_queue):
        """Test basic team initialization"""
        context = await init_team(
            api_key=api_key,
            agent_input_queue=mock_input_queue,
            max_messages=10
        )

        assert isinstance(context, AgentTeamContext)
        assert context.team is not None
        assert context.user_control is not None
        assert len(context.participant_names) > 0

    @pytest.mark.asyncio
    async def test_init_team_with_selector_prompt(self, api_key, mock_input_queue):
        """Test team initialization with custom selector"""
        custom_prompt = "Select the agent based on expertise"

        context = await init_team(
            api_key=api_key,
            agent_input_queue=mock_input_queue,
            selector_prompt=custom_prompt
        )

        assert context.team is not None

    @pytest.mark.asyncio
    async def test_participant_names_match_yaml(self, api_key, mock_input_queue):
        """Ensure participant names match YAML configuration"""
        data = load_data()
        expected_names = [agent["name"] for agent in data["agents"]]

        context = await init_team(
            api_key=api_key,
            agent_input_queue=mock_input_queue
        )

        assert set(context.participant_names) == set(expected_names)

    @pytest.mark.asyncio
    async def test_user_control_agent_created(self, api_key, mock_input_queue):
        """UserControlAgent should always be created"""
        context = await init_team(
            api_key=api_key,
            agent_input_queue=mock_input_queue
        )

        assert context.user_control is not None
        assert context.user_control.name == "You"

    @pytest.mark.asyncio
    async def test_team_has_termination_condition(self, api_key, mock_input_queue):
        """Team should have a termination condition"""
        context = await init_team(
            api_key=api_key,
            agent_input_queue=mock_input_queue,
            max_messages=5
        )

        assert hasattr(context.team, "_termination_condition")
        assert context.team._termination_condition is not None


class TestAgentConfiguration:
    @pytest.mark.asyncio
    async def test_agents_have_correct_names(self, api_key, mock_input_queue):
        """All agents should have names matching YAML config"""
        data = load_data()
        expected_names = {agent["name"] for agent in data["agents"]}

        context = await init_team(
            api_key=api_key,
            agent_input_queue=mock_input_queue
        )

        actual_names = set(context.participant_names)
        assert actual_names == expected_names

    @pytest.mark.asyncio
    async def test_orchestrator_exists(self, api_key, mock_input_queue):
        """Orchestrator agent should exist"""
        context = await init_team(
            api_key=api_key,
            agent_input_queue=mock_input_queue
        )

        assert "orchestrator" in context.participant_names

    @pytest.mark.asyncio
    async def test_specialist_agents_exist(self, api_key, mock_input_queue):
        """All specialist agents should exist"""
        context = await init_team(
            api_key=api_key,
            agent_input_queue=mock_input_queue
        )

        expected_specialists = [
            "bill_specialist",
            "committee_specialist",
            "actions_specialist",
            "amendment_specialist",
            "congress_member_specialist"
        ]

        for specialist in expected_specialists:
            assert specialist in context.participant_names


class TestModelClientConfiguration:
    @pytest.mark.asyncio
    async def test_model_client_created(self, api_key, mock_input_queue):
        """Model client should be properly configured"""
        context = await init_team(
            api_key=api_key,
            agent_input_queue=mock_input_queue
        )

        # Team should have model_client
        assert hasattr(context.team, "_model_client")
        assert context.team._model_client is not None


class TestSelectorConfiguration:
    @pytest.mark.asyncio
    async def test_default_selector_used_when_none_provided(self, api_key, mock_input_queue):
        """Default selector should be used when custom one not provided"""
        context = await init_team(
            api_key=api_key,
            agent_input_queue=mock_input_queue,
            selector_prompt=None
        )

        # Should have a selector function
        assert hasattr(context.team, "_selector_func")
        assert context.team._selector_func is not None

    @pytest.mark.asyncio
    async def test_custom_selector_enhanced(self, api_key, mock_input_queue):
        """Custom selector prompt should be enhanced via LLM"""
        custom_prompt = "Pick the best agent"

        context = await init_team(
            api_key=api_key,
            agent_input_queue=mock_input_queue,
            selector_prompt=custom_prompt
        )

        # Should still have a selector
        assert hasattr(context.team, "_selector_func")
        assert context.team._selector_func is not None
