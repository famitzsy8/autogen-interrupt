import asyncio

from dataclasses import dataclass

import configparser

# Read API key from secrets.ini
config = configparser.ConfigParser()
config.read('/Users/tofixjr/Desktop/Thesis/autogen-interrupt/secrets.ini')
api_key = config['API_KEYS']['OPENAI_API_KEY']
from openai import OpenAI
import requests

from autogen_core import (
    AgentId,
    ClosureAgent,
    ClosureContext,
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
    default_subscription,
    message_handler,
    type_subscription,
)

from openai import OpenAI

model_client = OpenAI(
    api_key=api_key,
)

TASK_RESULTS_TOPIC_TYPE = "task-results"
task_results_topic_id = TopicId(type=TASK_RESULTS_TOPIC_TYPE, source="default")

@dataclass
class WebSearchTask:
    task_id: str

@dataclass
class WebSearchResponse:
    task_id: str
    result: str


@type_subscription(topic_type="web-search")
class WebSearchAgent(RoutedAgent):


    def __init__(self, description: str, model_client: OpenAI):
        super().__init__(description)
        self._description = description
        self._model_client = model_client


    @message_handler
    async def on_task(self, message: WebSearchTask, ctx: MessageContext) -> None:
        print(f"{self._description} starting task {message.task_id}")
        response = self._model_client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[{"role": "user", "content": message.task_id}],
        )
        await self.publish_message(WebSearchResponse(task_id=message.task_id, result=response.choices[0].message.content), topic_id=task_results_topic_id)
    

async def main():

    runtime = SingleThreadedAgentRuntime()

    queue = asyncio.Queue[WebSearchResponse]()

    async def collect_result(_agent: ClosureContext, message: WebSearchResponse, ctx: MessageContext) -> None:
        await queue.put(message)
    
    await WebSearchAgent.register(runtime, "web_search_agent", lambda: WebSearchAgent("Web Search Agent", model_client))
    await WebSearchAgent.register(runtime, "web_search_agent_2", lambda: WebSearchAgent("Web Search Agent 2", model_client))
    runtime.start()

    CLOSURE_AGENT_TYPE = "collect_result_agent"

    await ClosureAgent.register_closure(
        runtime,
        CLOSURE_AGENT_TYPE,
        collect_result,
        subscriptions=lambda: [TypeSubscription(topic_type=TASK_RESULTS_TOPIC_TYPE, agent_type=CLOSURE_AGENT_TYPE)],
    )

    await runtime.publish_message(WebSearchTask(task_id="Search for all the information about autogen_coreRoutedAgent in a WebSearch"), topic_id=TopicId(type="web-search", source="default"))
    await runtime.publish_message(WebSearchTask(task_id="Search for all the information about autogen_agentchat.ChatAgent in a WebSearch"), topic_id=TopicId(type="web-search", source="default"))

    await runtime.stop_when_idle()

    while not queue.empty():
        print("-" * 100)
        print(await queue.get())
        print("-" * 100)

if __name__ == "__main__":
    asyncio.run(main())
