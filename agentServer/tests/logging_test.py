#!/usr/bin/env python3
"""
Simple logging test to understand AutoGen's actual output patterns.
This mimics autogen4.py but with normal console output to see timing and flow.
"""

import asyncio
import yaml
import logging
from typing import Sequence, List
import openai
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_ext.tools.mcp import McpWorkbench, StreamableHttpServerParams
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage

from util.api_clients import get_openai_client
from util.config_utils import _get_key

from PlannerAgent import PlannerAgent
from FilteredWorkbench import FilteredWorkbench
from autogen_agentchat.ui import Console

def _create_llm_selector(agent_names: List[str], prompt_cfg: dict, oai_key: str) -> callable:
    """Creates a closure for the selector function that has access to agent names."""
    def _llm_selector(thread: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
        last_msg = next((m for m in reversed(thread) if isinstance(m, BaseChatMessage)), None)
        if not last_msg:
            return None

        prompt = prompt_cfg["selector_prompt"]["description"].format(agent_names=agent_names, last_message=last_msg.content)

        openai.api_key = oai_key
        response = openai.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that selects the next agent to call."},
                {"role": "user", "content": prompt}
            ]
        )
        model_result = type("ModelResult", (), {"content": response.choices[0].message.content})()

        if model_result.content.strip() in agent_names:
            return model_result.content.strip()
        else:
            return None

    return _llm_selector

async def run_logging_test(company_name: str = "ExxonMobil", bill: str = "hr2307-117") -> None:
    """Run the 2-agent investigation with normal console logging to observe patterns"""
    
    print("=" * 80)
    print(f"🔬 LOGGING TEST: {company_name} - {bill}")
    print("=" * 80)
    print("📝 This will show the actual AutoGen message flow and timing")
    print("🕒 Watch for message types, sources, and content patterns")
    print("=" * 80)
    
    # -------------------- Config & constants --------------------
    advancement = "advancement"
    selected_agent_names = ["committee_specialist", "orchestrator"]
    local_path = os.path.dirname(os.path.abspath(__file__))

    # -------------------- Load YAML configs --------------------
    with open(f"{local_path}/config/agents_4.yaml", "r") as f:
        agents_cfg = yaml.safe_load(f)
    with open(f"{local_path}/config/tasks_4.yaml", "r") as f:
        tasks_cfg = yaml.safe_load(f)
    with open(f"{local_path}/config/prompt.yaml", "r") as f:
        prompt_cfg = yaml.safe_load(f)

    # -------------------- Model client --------------------
    try:
        oai_key = _get_key("OPENAI_API_KEY")
    except Exception as e:
        print(f"⚠️  API key loading failed: {e}")
        print("💡 Trying alternative approach...")
        
        # Try loading directly from secrets.ini
        import configparser
        import os
        config = configparser.ConfigParser()
        secrets_paths = [
            "/app/secrets.ini",
            "/app/agentServer/secrets.ini", 
            "secrets.ini"
        ]
        
        oai_key = None
        for path in secrets_paths:
            if os.path.exists(path):
                config.read(path)
                try:
                    oai_key = config["API_KEYS"]["OPENAI_API_KEY"]
                    print(f"✅ Found API key in {path}")
                    break
                except KeyError:
                    continue
        
        if not oai_key:
            print("❌ Could not find OpenAI API key")
            return
    
    model_client = OpenAIChatCompletionClient(model="gpt-4.1", api_key=oai_key)

    # -------------------- Workbench setup --------------------
    print("🔗 Setting up MCP connection to ragmcp server...")
    # Connect to ragMCP server running in separate Docker container
    ragmcp_url = os.getenv("RAGMCP_URL", "http://ragmcp:8080")
    params = StreamableHttpServerParams(
        url=ragmcp_url,
        timeout_seconds=60,
    )

    async with McpWorkbench(server_params=params) as workbench:
        print("✅ MCP connection established")
        
        allowed_tool_names_comm = ["get_committee_members", "get_committee_actions", "getBillCommittees"]
        workbench_comm = FilteredWorkbench(workbench, allowed_tool_names_comm)

        termination_condition = TextMentionTermination("TERMINATE")

        print("🤖 Creating agents...")
        
        # Create committee specialist
        committee_specialist = PlannerAgent(
            name="committee_specialist",
            description=agents_cfg["committee_specialist"]["description"].format(
                advancement=advancement, 
                agent_names=selected_agent_names, 
                company_name=company_name
            ),
            model_client=model_client,
            workbench=workbench_comm,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        # Create orchestrator
        orchestrator = AssistantAgent(
            name="orchestrator",
            description=agents_cfg["orchestrator"]["description"].format(
                bill=bill,
                advancement=advancement,
                agent_names=["committee_specialist"],
                company_name=company_name
            ),
            model_client=model_client,
            model_client_stream=True,
        )

        agents = [committee_specialist, orchestrator]
        agent_names = [agent.name for agent in agents]

        print(f"✅ Created {len(agents)} agents: {agent_names}")

        # Create the selector function
        llm_selector = _create_llm_selector(agent_names=agent_names, prompt_cfg=prompt_cfg, oai_key=oai_key)

        # Create team
        team = SelectorGroupChat(
            agents,
            termination_condition=termination_condition,
            selector_func=llm_selector,
            model_client=model_client,
            max_turns=5  # Keep it short for observation
        )

        print("🏁 Starting investigation with normal console logging...")
        print("=" * 80)

        # Run the investigation with normal Console (like autogen4.py)
        task_description = tasks_cfg["main_task"]["description"].format(
            bill=bill, 
            advancement=advancement, 
            company_name=company_name
        )
        
        # This will give us the same output as autogen4.py
        await Console(team.run_stream(task=task_description))
        
        print("=" * 80)
        print("✅ Logging test completed!")
        print("📊 Review the output above to understand message patterns")

if __name__ == "__main__":
    # Run the logging test
    asyncio.run(run_logging_test())