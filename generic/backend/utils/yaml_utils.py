"""Utility functions for reading YAML configuration files."""

import yaml
from pathlib import Path
from typing import List


def get_agent_team_names() -> List[str]:
    # Scan factory directory for .yaml files and extract team_name field from each
    team_names = []
    factory_dir = Path(__file__).parent.parent / "factory"

    for yaml_file in factory_dir.glob("*.yaml"):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data and "team_name" in data:
                    team_names.append(data["team_name"])
        except Exception as e:
            print(f"Warning: Could not read team_name from {yaml_file}: {e}")
            continue

    return team_names


def load_team_config_by_name(team_name: str) -> dict:
    # Find and load YAML config that matches the given team_name
    factory_dir = Path(__file__).parent.parent / "factory"

    for yaml_file in factory_dir.glob("*.yaml"):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data and data.get("team_name") == team_name:
                    return data
        except Exception:
            continue

    # Team not found
    available = get_agent_team_names()
    raise ValueError(f"Team '{team_name}' not found. Available: {available}")

def get_team_main_tasks() -> str:
    """
    Scan factory directory for .yaml files and return the main_task description string.
    Only includes yaml files with both 'team_name' and 'tasks.main_task.description' present.
    """
    factory_dir = Path(__file__).parent.parent / "factory"
    print("Trying to get initial task")
    for yaml_file in factory_dir.glob("*.yaml"):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if (
                    data
                    and "team_name" in data
                    and "tasks" in data
                    and isinstance(data["tasks"], dict)
                    and "main_task" in data["tasks"]
                ):
                    main_task = data["tasks"]["main_task"]
                    return main_task["description"]
                    
        except Exception as e:
            print(f"Warning: Could not read main_task from {yaml_file}: {e}")
            continue

    raise ValueError("Task extraction failed")


def get_summarization_system_prompt() -> str:
    """
    Scan factory directory for .yaml files and return the summarization_system_prompt string.
    Only includes yaml files with both 'team_name' and 'prompts.summarization_system_prompt' present.
    """
    factory_dir = Path(__file__).parent.parent / "factory"

    for yaml_file in factory_dir.glob("*.yaml"):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if (
                    data
                    and "team_name" in data
                    and "prompts" in data
                    and isinstance(data["prompts"], dict)
                    and "summarization_system_prompt" in data["prompts"]
                ):
                    return data["prompts"]["summarization_system_prompt"]

        except Exception as e:
            print(f"Warning: Could not read summarization_system_prompt from {yaml_file}: {e}")
            continue

    raise ValueError("Summarization system prompt extraction failed")

