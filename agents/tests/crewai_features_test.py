from crewai import Agent, Task, Crew, Process
from crewai import LLM
from crewai_tools import MCPServerAdapter
from crewai.project import CrewBase, agent, crew, task
from mcp import StdioServerParameters
import os
import yaml
from agents.util.api_util import __get_api_keys

oai_key, gai_key = __get_api_keys()
print(oai_key, gai_key)

gemini_flash = LLM(model="gemini/gemini-2.0-flash",
    temperature=0.7,api_key=gai_key)

gpt4o_mini = LLM("openai/gpt-4o-mini", temperature=0.7, api_key=oai_key)

function_calling_llm = gpt4o_mini
MAX_ITER = 5
MAX_RPM = 30000
RESPONSE_TEMPLATE = ...


server_params=StdioServerParameters(
    command="python", 
    args=["congressMCP/main.py"]
)

agents_config_file = "./agents/tests/config/agents.yaml"
tasks_config_file = "./agents/tests/config/tasks.yaml"

with MCPServerAdapter(server_params) as mcp_tools:
#     @CrewBase
#     class FeaturesTest:

#         @agent
#         def actions_agent(self) -> Agent:
#             return Agent(
#             config=self.agents_config['actions_agent'], # type: ignore[index]
#             verbose=True,
#             tools=mcp_tools,
#             llm=gpt4o_mini
#             )

#         @agent
#         def retrieval_agent(self) -> Agent:
#             return Agent(
#             config=self.agents_config['retrieval_agent'], # type: ignore[index]
#             verbose=True,
#             llm=gemini_flash,
#             tools=mcp_tools
#             )

#         @task
#         def big_task(self) -> Task:
#             return Task(
#             config=self.tasks_config['big_task'], # type: ignore[index]
#             context=[self.retrieval_task()]
#             )

#         @task
#         def retrieval_task(self) -> Task:
#             return Task(
#             config=self.tasks_config['retrieval_task'] # type: ignore[index]
#             )

#         @crew
#         def crew(self) -> Crew:
#             return Crew(
#                 agents=[
#                     self.actions_agent(),
#                     self.retrieval_agent()
#                 ],
#                 tasks=[
#                     self.retrieval_task(),
#                     self.big_task()
#                 ],
#                 process=Process.hierarchical,
#                 manager_llm=gpt4o_mini,
#                 verbose=True
#             )

    # ================= NEW MULTI-AGENT LOBBYING WORKFLOW =================
    @CrewBase
    class LobbyingWorkflow:

        # ----- Agent builders -----
        @agent
        def coordinator_agent(self) -> Agent:
            return Agent(
                config=self.agents_config['coordinator_agent'],  # type: ignore[index]
                verbose=True,
                llm=gpt4o_mini
            )

        @agent
        def actions_overview_agent(self) -> Agent:
            return Agent(
                config=self.agents_config['actions_overview_agent'],  # type: ignore[index]
                verbose=True,
                llm=gpt4o_mini
            )

        @agent
        def committee_agent(self) -> Agent:
            return Agent(
                config=self.agents_config['committee_agent'],  # type: ignore[index]
                verbose=True,
                tools=mcp_tools,
                llm=gemini_flash
            )

        @agent
        def amendment_agent(self) -> Agent:
            return Agent(
                config=self.agents_config['amendment_agent'],  # type: ignore[index]
                verbose=True,
                tools=mcp_tools,
                llm=gemini_flash
            )

        @agent
        def bill_text_agent(self) -> Agent:
            return Agent(
                config=self.agents_config['bill_text_agent'],  # type: ignore[index]
                verbose=True,
                tools=mcp_tools,
                llm=gemini_flash
            )

        @agent
        def data_fetch_agent(self) -> Agent:
            return Agent(
                config=self.agents_config['data_fetch_agent'],  # type: ignore[index]
                verbose=True,
                tools=mcp_tools,
                llm=gemini_flash
            )

        # ----- Tasks -----
        @task
        def data_fetch_task(self) -> Task:
            return Task(
                config=self.tasks_config['data_fetch_task']  # type: ignore[index]
            )

        @task
        def committee_task(self) -> Task:
            return Task(
                config=self.tasks_config['committee_task'],  # type: ignore[index]
                context=[self.data_fetch_task()]
            )

        @task
        def amendment_task(self) -> Task:
            return Task(
                config=self.tasks_config['amendment_task'],  # type: ignore[index]
                context=[self.data_fetch_task()]
            )

        @task
        def bill_text_task(self) -> Task:
            return Task(
                config=self.tasks_config['bill_text_task'],  # type: ignore[index]
                context=[self.data_fetch_task()]
            )

        @task
        def actions_overview_task(self) -> Task:
            return Task(
                config=self.tasks_config['actions_overview_task'],  # type: ignore[index]
                context=[
                    self.data_fetch_task(),
                    self.committee_task(),
                    self.amendment_task()
                ]
            )

        @task
        def coordination_task(self) -> Task:
            return Task(
                config=self.tasks_config['coordination_task'],  # type: ignore[index]
                context=[
                    self.actions_overview_task(),
                    self.bill_text_task()
                ]
            )

        # ----- Crew -----
        @crew
        def crew(self) -> Crew:
            return Crew(
                agents=[
                    self.coordinator_agent(),
                    self.actions_overview_agent(),
                    self.committee_agent(),
                    self.amendment_agent(),
                    self.bill_text_agent(),
                    self.data_fetch_agent()
                ],
                tasks=[
                    self.data_fetch_task(),
                    self.committee_task(),
                    self.amendment_task(),
                    self.bill_text_task(),
                    self.actions_overview_task(),
                    self.coordination_task()
                ],
                process=Process.hierarchical,
                manager_llm=gpt4o_mini,
                verbose=True
            )

    # -------------- RUN THE NEW WORKFLOW --------------
    workflow = LobbyingWorkflow()
    result = workflow.crew().kickoff(inputs={
        "bill": "s3688-116",
        "company": "ExxonMobil"
    })
    print(result)
