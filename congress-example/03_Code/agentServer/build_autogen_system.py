import asyncio
import yaml
import openai
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, SseServerParams
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.agents import AssistantAgent
from util.config import _get_key
from util.PlannerAgent import PlannerAgent
from FilteredWorkbench import FilteredWorkbench
from autogen_agentchat.ui import Console
import os
import configparser
import random  # For random agent selection if needed
import importlib

def _create_llm_selector(agent_names, prompt_template, oai_key, selector_model):
    def llm_selector(thread):
        last_msg = next((m for m in reversed(thread) if isinstance(m, BaseChatMessage)), None)
        if not last_msg:
            return None

        prompt = prompt_template.format(agent_names=agent_names, last_message=last_msg.content)

        openai.api_key = oai_key
        response = openai.chat.completions.create(
            model=selector_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that selects the next agent to call."},
                {"role": "user", "content": prompt}
            ]
        )
        model_result = response.choices[0].message.content.strip()

        # Handle special cases from prompt logic
        if "returning his findings" in last_msg.content.lower():
            return "orchestrator"
        elif "asking all of the agents for confirmation" in last_msg.content.lower():
            return random.choice(agent_names)

        if model_result in agent_names:
            return model_result
        else:
            return None

    return llm_selector

async def run_from_yaml(yaml_path, company_name, bill, year=None, websocket_callback=None):
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)

    # Load API key
    oai_key = _get_key("OPENAI_API_KEY")

    # Model client
    model_client = OpenAIChatCompletionClient(model=config['model']['name'], api_key=oai_key)

    # Workbench setup
    params = SseServerParams(url=config['workbench']['url'], timeout=config['workbench']['timeout'])
    async with McpWorkbench(server_params=params) as base_workbench:
        # Create filtered workbenches
        filtered_workbenches = {}
        for key, tools in config['filtered_tools'].items():
            filtered_workbenches[key] = FilteredWorkbench(base_workbench, tools)

        # Agent names
        agent_names = [a['name'] for a in config['agents']]

        # Create agents dynamically using class from YAML
        agents = []
        for a in config['agents']:
            # Conditional kwargs for formatting
            format_kwargs = {'agent_names': agent_names, 'company_name': company_name}
            if '{bill}' in a['description_template']:
                format_kwargs['bill'] = bill
            desc = a['description_template'].format(**format_kwargs)

            # Dynamically load agent class
            agent_class_name = a.get('class', 'PlannerAgent')
            if agent_class_name == 'PlannerAgent':
                agent_class = PlannerAgent
            elif agent_class_name == 'AssistantAgent':
                agent_class = AssistantAgent
            else:
                # Try to import from util or autogen_agentchat.agents
                try:
                    module = importlib.import_module('util.' + agent_class_name)
                    agent_class = getattr(module, agent_class_name)
                except (ModuleNotFoundError, AttributeError):
                    try:
                        module = importlib.import_module('autogen_agentchat.agents')
                        agent_class = getattr(module, agent_class_name)
                    except (ModuleNotFoundError, AttributeError):
                        raise ValueError(f"Could not load agent class: {agent_class_name}")
            
            agent = agent_class(
                name=a['name'],
                description=desc,
                model_client=model_client,
                workbench=filtered_workbenches[a['workbench']],
                model_client_stream=a['stream'],
                reflect_on_tool_use=a.get('reflect', False)
            )
            agents.append(agent)

        # Selector
        selector_prompt = config['selector']['prompt_template']
        selector_model = config['selector']['model']
        selector_func = _create_llm_selector(agent_names, selector_prompt, oai_key, selector_model)

        # Team setup using class from YAML
        team_class_name = config.get('team', {}).get('class', 'SelectorGroupChat')
        if team_class_name == 'SelectorGroupChat':
            team_class = SelectorGroupChat
        else:
            # Try to dynamically import team class
            try:
                module = importlib.import_module('autogen_agentchat.teams')
                team_class = getattr(module, team_class_name)
            except (ModuleNotFoundError, AttributeError):
                raise ValueError(f"Could not load team class: {team_class_name}")
        
        termination_condition = TextMentionTermination(config['termination'])
        team = team_class(
            agents,
            termination_condition=termination_condition,
            selector_func=selector_func,
            model_client=model_client,
            max_turns=config['max_turns']
        )

        # Task
        effective_year = year or config['year']
        task = config['task_template'].format(year=effective_year, bill_name=bill, company_name=company_name)

        # Run
        await Console(team.run_stream(task=task))

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python build_autogen_system.py <yaml_path> <company_name> <bill> [year]")
        sys.exit(1)
    yaml_path = sys.argv[1]
    company_name = sys.argv[2]
    bill = sys.argv[3]
    year = int(sys.argv[4]) if len(sys.argv) > 4 else None
    asyncio.run(run_from_yaml(yaml_path, company_name, bill, year))
