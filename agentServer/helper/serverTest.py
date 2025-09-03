import asyncio
import yaml
import logging
from typing import Sequence, List
import openai
from autogen_ext.models.openai import OpenAIChatCompletionClient
import os

from autogen_ext.tools.mcp import McpWorkbench, StreamableHttpServerParams
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage

from util.config_utils import _get_key

from util.PlannerAgent import PlannerAgent
from helper.FilteredWorkbench import FilteredWorkbench
from helper.stream_accumulator import StreamAccumulator

# Event emitter for WebSocket communication
class AutoGenEventEmitter:
    def __init__(self, websocket_callback=None):
        self.websocket_callback = websocket_callback
        
    def emit_agent_communication(self, agent_name: str, message_type: str, content: str, tool_calls=None):
        """Emit agent communication event"""
        event = {
            "type": "agent_communication",
            "timestamp": asyncio.get_event_loop().time(),
            "data": {
                "id": f"{agent_name}_{asyncio.get_event_loop().time()}",
                "agent": agent_name,
                "type": message_type,
                "simplified": content[:200] + "..." if len(content) > 200 else content,
                "fullContent": content,
                "toolCalls": tool_calls or [],
                "status": "completed"
            }
        }
        if self.websocket_callback:
            asyncio.create_task(self.websocket_callback(event))
    
    def emit_tool_call_start(self, tool_name: str, arguments: dict, agent_name: str):
        """Emit tool call start event"""
        event = {
            "type": "tool_call_start", 
            "timestamp": asyncio.get_event_loop().time(),
            "data": {
                "id": f"tool_{tool_name}_{asyncio.get_event_loop().time()}",
                "name": tool_name,
                "arguments": arguments,
                "agent": agent_name,
                "status": "in_progress"
            }
        }
        if self.websocket_callback:
            asyncio.create_task(self.websocket_callback(event))
    
    def emit_tool_call_result(self, tool_name: str, result: any, success: bool, agent_name: str):
        """Emit tool call result event"""
        event = {
            "type": "tool_call_result",
            "timestamp": asyncio.get_event_loop().time(),
            "data": {
                "id": f"tool_{tool_name}_{asyncio.get_event_loop().time()}",
                "name": tool_name,
                "result": result,
                "success": success,
                "agent": agent_name,
                "status": "completed" if success else "failed"
            }
        }
        if self.websocket_callback:
            asyncio.create_task(self.websocket_callback(event))
    
    def emit_investigation_complete(self, final_results):
        """Emit investigation completion event"""
        event = {
            "type": "investigation_complete",
            "timestamp": asyncio.get_event_loop().time(),
            "data": final_results
        }
        if self.websocket_callback:
            asyncio.create_task(self.websocket_callback(event))

# Global event emitter
event_emitter = AutoGenEventEmitter()

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

        # Note: Removed handoff event emission to fix "only Handoff boxes" issue

        if model_result.content.strip() in agent_names:
            return model_result.content.strip()
        else:
            return None

    return _llm_selector

class DirectStreamingConsole:
    """Console that processes AutoGen stream messages directly with StreamAccumulator"""
    
    def __init__(self, stream_generator, websocket_callback=None):
        self.stream_generator = stream_generator
        self.websocket_callback = websocket_callback
        # Use default 2-agent setup for serverTest
        self.accumulator = StreamAccumulator(websocket_callback, ['orchestrator', 'committee_specialist'])
        
    async def run(self):
        """Process the stream by feeding messages directly to accumulator"""
        try:
            async for message in self.stream_generator:
                await self.accumulator.process_stream_message(message)
                    
        except Exception as e:
            print(f"Error in direct streaming console: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Finalize any remaining message
            await self.accumulator.finish()
            
            # Emit completion
            if self.websocket_callback:
                await self.websocket_callback({
                    "type": "investigation_complete",
                    "timestamp": asyncio.get_event_loop().time(),
                    "data": {
                        "status": "completed",
                        "message": "Investigation finished"
                    }
                })

async def run_investigation(company_name: str, bill: str, websocket_callback=None) -> None:
    """Run the simplified AutoGen investigation with only orchestrator and committee_specialist"""
    
    # Set up event emitter with websocket callback
    global event_emitter
    event_emitter.websocket_callback = websocket_callback
    
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
    # Connect to ragMCP server running in separate Docker container
    ragmcp_url = os.getenv("RAGMCP_URL", "http://ragmcp:8080")
    params = StreamableHttpServerParams(
        url=ragmcp_url,
        timeout_seconds=60,
    )

    async with McpWorkbench(server_params=params) as workbench:
        allowed_tool_names_comm = ["get_committee_members", "get_committee_actions", "getBillCommittees"]
        workbench_comm = FilteredWorkbench(workbench, allowed_tool_names_comm)

        termination_condition = TextMentionTermination("TERMINATE")

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

        # Create the selector function
        llm_selector = _create_llm_selector(agent_names=agent_names, prompt_cfg=prompt_cfg, oai_key=oai_key)

        # Create team
        team = SelectorGroupChat(
            agents,
            termination_condition=termination_condition,
            selector_func=llm_selector,
            model_client=model_client,
            max_turns=10  # Limited for testing
        )

        # Emit investigation start
        event_emitter.emit_agent_communication(
            "orchestrator",
            "message", 
            f"Starting investigation of {company_name} lobbying activities for {bill}"
        )

        # Run the investigation with intelligent console
        task_description = tasks_cfg["main_task"]["description"].format(
            bill=bill, 
            advancement=advancement, 
            company_name=company_name
        )
        
        console = DirectStreamingConsole(
            team.run_stream(task=task_description),
            websocket_callback
        )
        await console.run()

if __name__ == "__main__":
    # Test run
    asyncio.run(run_investigation("ExxonMobil", "hr2307-117"))