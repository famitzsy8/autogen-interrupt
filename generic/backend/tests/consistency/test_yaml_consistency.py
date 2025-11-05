"""Test YAML configuration consistency and validity"""

import pytest
import yaml
from pathlib import Path
from factory.team_factory import load_data


class TestYAMLConsistency:
    def test_all_agents_have_required_fields(self):
        """Every agent must have required configuration"""
        data = load_data()
        required_fields = ["description", "agent_class", "system_message", "name"]

        for agent_name, agent in data["agents"].items():
            for field in required_fields:
                assert field in agent, f"Agent {agent_name} missing {field}"

    def test_agent_names_unique(self):
        """Agent names must be unique (checked via dict keys)"""
        data = load_data()
        # Dict keys are inherently unique, but verify 'name' fields match keys
        for agent_name, agent in data["agents"].items():
            assert agent["name"] == agent_name, f"Agent name mismatch: key='{agent_name}' vs name='{agent['name']}'"

    def test_agent_classes_exist(self):
        """All referenced agent classes should be importable"""
        data = load_data()

        for agent_name, agent in data["agents"].items():
            agent_class = agent["agent_class"]
            # Try to import the class
            if agent_class == "PlannerAgent":
                from agents.PlannerAgent import PlannerAgent
                assert PlannerAgent is not None
            elif agent_class == "AssistantAgent":
                from autogen_agentchat.agents import AssistantAgent
                assert AssistantAgent is not None
            elif agent_class == "UserProxyAgent":
                from autogen_agentchat.agents import UserProxyAgent
                assert UserProxyAgent is not None
            else:
                pytest.fail(f"Unknown agent class: {agent_class}")

    def test_workbench_classes_exist(self):
        """All referenced workbench classes should be importable"""
        data = load_data()

        for agent_name, agent in data["agents"].items():
            if "tools" in agent:
                workbench_class = agent["tools"]["workbench_class"]
                if workbench_class == "FilteredWorkbench":
                    from tools.FilteredWorkbench import FilteredWorkbench
                    assert FilteredWorkbench is not None
                else:
                    pytest.fail(f"Unknown workbench class: {workbench_class}")

    def test_group_chat_class_exists(self):
        """Group chat class should be valid"""
        data = load_data()
        gc_class = data["team"]["group_chat_class"]

        if gc_class == "SelectorGroupChat":
            from autogen_agentchat.teams import SelectorGroupChat
            assert SelectorGroupChat is not None
        elif gc_class == "RoundRobinGroupChat":
            from autogen_agentchat.teams import RoundRobinGroupChat
            assert RoundRobinGroupChat is not None
        else:
            pytest.fail(f"Unknown group chat class: {gc_class}")

    def test_mcp_url_format(self):
        """MCP URL should be properly formatted if present"""
        data = load_data()
        mcp_url = data["team"].get("mcp_url")

        if mcp_url:
            assert mcp_url.startswith("http://") or mcp_url.startswith("https://"), \
                "MCP URL must start with http:// or https://"

    def test_selector_prompt_references_correct_variables(self):
        """Default selector prompt should use correct template variables"""
        data = load_data()
        prompt = data["team"]["group_chat_args"]["default_selector_prompt"]

        # Should contain expected template variables
        assert "{last_message}" in prompt
        assert "{agent_names}" in prompt

    def test_llm_configuration(self):
        """LLM configuration should be valid"""
        data = load_data()
        llm = data["llm"]

        assert "model_client_class" in llm
        assert "model_client_args" in llm
        assert "model" in llm["model_client_args"]

    def test_agent_names_valid_identifiers(self):
        """Agent names should be valid Python identifiers (no spaces, special chars)"""
        data = load_data()

        for agent_name, agent in data["agents"].items():
            name = agent["name"]
            # Should not contain spaces
            assert " " not in name, f"Agent name '{name}' contains spaces"
            # Should not be empty
            assert name.strip() != "", f"Agent name is empty or whitespace"

    def test_tool_names_are_lists(self):
        """Tool names should be lists of strings"""
        data = load_data()

        for agent_name, agent in data["agents"].items():
            if "tools" in agent:
                tool_names = agent["tools"]["allowed_tool_names"]
                assert isinstance(tool_names, list), \
                    f"Agent {agent['name']} tool names should be a list"
                for tool in tool_names:
                    assert isinstance(tool, str), \
                        f"Tool name in {agent['name']} should be string"

    def test_max_turns_is_positive(self):
        """Max turns should be a positive integer"""
        data = load_data()
        max_turns = data["team"]["group_chat_args"]["max_turns"]

        assert isinstance(max_turns, int), "max_turns should be an integer"
        assert max_turns > 0, "max_turns should be positive"

    def test_model_client_stream_is_boolean(self):
        """model_client_stream should be boolean if present"""
        data = load_data()

        for agent_name, agent in data["agents"].items():
            if "model_client_stream" in agent:
                assert isinstance(agent["model_client_stream"], bool), \
                    f"Agent {agent['name']} model_client_stream should be boolean"

    def test_reflect_on_tool_use_is_boolean(self):
        """reflect_on_tool_use should be boolean if present"""
        data = load_data()

        for agent_name, agent in data["agents"].items():
            if "reflect_on_tool_use" in agent:
                assert isinstance(agent["reflect_on_tool_use"], bool), \
                    f"Agent {agent['name']} reflect_on_tool_use should be boolean"

    def test_has_user_proxy_is_boolean(self):
        """has_user_proxy should be boolean"""
        data = load_data()
        has_user_proxy = data["team"]["group_chat_args"]["has_user_proxy"]

        assert isinstance(has_user_proxy, bool), "has_user_proxy should be boolean"

    def test_user_proxy_name_consistent(self):
        """If has_user_proxy is true, user_proxy_name should be non-empty"""
        data = load_data()
        has_user_proxy = data["team"]["group_chat_args"]["has_user_proxy"]
        user_proxy_name = data["team"]["group_chat_args"].get("user_proxy_name", "")

        if has_user_proxy:
            assert user_proxy_name.strip() != "", \
                "user_proxy_name should be non-empty when has_user_proxy is true"

    def test_mcp_timeout_is_positive(self):
        """MCP timeout should be positive if present"""
        data = load_data()
        timeout = data["team"].get("mcp_timeout")

        if timeout is not None:
            assert isinstance(timeout, (int, float)), "mcp_timeout should be numeric"
            assert timeout > 0, "mcp_timeout should be positive"


class TestYAMLStructure:
    def test_yaml_is_valid(self):
        """YAML file should be valid and parseable"""
        try:
            data = load_data()
            assert data is not None
            assert isinstance(data, dict)
        except yaml.YAMLError as e:
            pytest.fail(f"YAML parsing failed: {e}")

    def test_top_level_keys_present(self):
        """All required top-level keys should be present"""
        data = load_data()
        required_keys = ["agents", "team", "llm"]

        for key in required_keys:
            assert key in data, f"Missing top-level key: {key}"

    def test_agents_is_dict(self):
        """agents should be a dict"""
        data = load_data()
        assert isinstance(data["agents"], dict), "agents should be a dict"
        assert len(data["agents"]) > 0, "agents dict should not be empty"

    def test_team_is_dict(self):
        """team should be a dictionary"""
        data = load_data()
        assert isinstance(data["team"], dict), "team should be a dictionary"

    def test_llm_is_dict(self):
        """llm should be a dictionary"""
        data = load_data()
        assert isinstance(data["llm"], dict), "llm should be a dictionary"


class TestAgentDescriptions:
    def test_all_descriptions_non_empty(self):
        """All agent descriptions should be non-empty"""
        data = load_data()

        for agent_name, agent in data["agents"].items():
            desc = agent["description"]
            assert desc.strip() != "", f"Agent {agent_name} has empty description"

    def test_descriptions_are_strings(self):
        """All descriptions should be strings"""
        data = load_data()

        for agent_name, agent in data["agents"].items():
            assert isinstance(agent["description"], str), \
                f"Agent {agent_name} description should be a string"

    def test_descriptions_reference_company_placeholders(self):
        """Descriptions should use {company_name} placeholder consistently"""
        data = load_data()

        # At least some agents should reference company_name
        has_company_reference = False
        for agent_name, agent in data["agents"].items():
            if "{company_name}" in agent["description"]:
                has_company_reference = True
                break

        # This is a soft check - at least one should reference it
        assert has_company_reference, "No agent descriptions reference {company_name}"


class TestPromptConfiguration:
    def test_prompts_section_exists(self):
        """Prompts section should exist if referenced"""
        data = load_data()

        # Prompts are optional but if present should be valid
        if "prompts" in data:
            assert isinstance(data["prompts"], dict)

    def test_planning_prompt_exists_if_planner_agents_present(self):
        """If PlannerAgent is used, planning_prompt should exist"""
        data = load_data()

        has_planner = any(
            agent["agent_class"] == "PlannerAgent"
            for agent_name, agent in data["agents"].items()
        )

        if has_planner and "prompts" in data:
            assert "planning_prompt" in data["prompts"], \
                "planning_prompt should exist when PlannerAgent is used"


class TestTaskConfiguration:
    def test_tasks_section_valid_if_present(self):
        """Tasks section should be valid if present"""
        data = load_data()

        if "tasks" in data:
            assert isinstance(data["tasks"], dict), "tasks should be a dictionary"

    def test_main_task_exists_if_tasks_present(self):
        """main_task should exist in tasks section"""
        data = load_data()

        if "tasks" in data:
            # At least one task should be defined
            assert len(data["tasks"]) > 0, "tasks section should not be empty"


class TestParamsClassConfiguration:
    def test_params_class_valid_if_mcp_used(self):
        """If MCP URL is set, params_class should be valid"""
        data = load_data()
        mcp_url = data["team"].get("mcp_url")
        params_class = data["team"].get("params_class")

        if mcp_url:
            assert params_class is not None, \
                "params_class should be set when mcp_url is present"
            assert params_class in ["StdioServerParams", "SseServerParams"], \
                f"Invalid params_class: {params_class}"

    def test_params_class_importable(self):
        """params_class should be importable"""
        data = load_data()
        params_class = data["team"].get("params_class")

        if params_class:
            if params_class == "StdioServerParams":
                from autogen_ext.tools.mcp import StdioServerParams
                assert StdioServerParams is not None
            elif params_class == "SseServerParams":
                from autogen_ext.tools.mcp import SseServerParams
                assert SseServerParams is not None
