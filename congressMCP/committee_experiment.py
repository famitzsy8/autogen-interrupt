from crewai.project import CrewBase, agent, crew, task

import os, argparse, asyncio
from crewai import Crew, Agent, Task, LLM, Process
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters
from util.api_util import __get_api_keys

parser = argparse.ArgumentParser()
parser.add_argument("--bill",    required=True, help="e.g. s3094-115")
parser.add_argument("--company", required=True, help="e.g. ExxonMobil")
args = parser.parse_args()

_, oai_key, gai_key, _ = __get_api_keys()

server_params=StdioServerParameters(
    command="python", 
    args=["congressMCP/main.py"]
)

agents_config_file = "./congressMCP/config/agents.yaml"
tasks_config_file = "./congressMCP/config/tasks.yaml"

gemini_flash = LLM(model="gemini/gemini-2.0-flash",
    temperature=0.7,api_key=gai_key)

gpt4o_mini = LLM("openai/gpt-4o-mini", temperature=0.7, api_key=oai_key)

function_calling_llm = gpt4o_mini

with MCPServerAdapter(server_params) as mcp_tools:
    @CrewBase
    class LobbyingWorkflow:

        # ----- Agent builders -----
        @agent
        def orchestrator_agent(self) -> Agent:
            return Agent(
                config=self.agents_config['orchestrator_agent'],  # type: ignore[index]
                verbose=True,
                llm=gpt4o_mini,
                tools=mcp_tools,
            )
        
        @task
        def orchestrator_task(self) -> Task:
            return Task(
                config=self.tasks_config['orchestrator_task'],  # type: ignore[index]
                context=[
                    self.orchestrator_agent()
                ]
            )
        
        @crew
        def crew(self) -> Crew:
            return Crew(
                agents=[
                    self.orchestrator_agent()
                ],
                tasks=[
                    self.orchestrator_task(),
                ],
                process=Process.hierarchical,
                manager_llm=gpt4o_mini,
                verbose=True
            )
        

