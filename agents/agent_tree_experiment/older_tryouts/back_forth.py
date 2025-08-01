# Define three agents: One that is the committee specialist, one that is the bill text specialist, and one that is the actions specialist.
# Here I would like to build a back and forth conversation between the three agents, that is not sequential, and pre-programmed.

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from util.api_util import __get_api_keys
import asyncio
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from typing import Sequence
import random


oai_key, _ = __get_api_keys()
model_client = OpenAIChatCompletionClient(
    model="gpt-4o-mini",
    api_key=oai_key
)


class LobbyingGroupChat(SelectorGroupChat):
    def __init__(self, participants, model_client, termination_condition, max_turns, selector_prompt, selector_func):
        super().__init__(participants, model_client, termination_condition, selector_func)
        self._participants = participants
        self._model_client = model_client
        self._termination_condition = termination_condition
        self._max_turns = max_turns
        self.selector_func = selector_func
        self._selector_prompt = selector_prompt

async def main():
    params = StdioServerParams(
        command="python",
        args=["congressMCP/main.py"],
        read_timeout_seconds=60,
    )

    # You can also use `start()` and `stop()` to manage the session.
    async with McpWorkbench(server_params=params) as workbench:
        tools = await workbench.list_tools()
        print(tools)
        # # 2. Define the agents, each with access to the MCP tools
        # committee_agent = AssistantAgent(
        #     name="committee_specialist",
        #     description="You are the specialist in everything related to committees in the United States Congress.",
        #     model_client=model_client,
        #     workbench=[tools]
        # )

        # bill_text_agent = AssistantAgent(
        #     name="bill_text_specialist",
        #     description="You are the specialist in everything related to the text of bills in the United States Congress.",
        #     model_client=model_client
        # )

        # actions_agent = AssistantAgent(
        #     name="actions_specialist",
        #     description="You are the specialist in everything related to the legislative actions of the United States Congress.",
        #     model_client=model_client
        # )

        # termination_condition = TextMentionTermination("TERMINATE")
        def selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
            if (len(messages) == 1):
                return "committee_specialist"
            else:
                return random.choice(["bill_text_specialist", "actions_specialist"])

        # chat = SelectorGroupChat(
        #     participants=[committee_agent, bill_text_agent, actions_agent],
        #     model_client=model_client,
        #     termination_condition=termination_condition,
        #     max_turns=20,
        #     selector_func=selector_func
        # )


        # await Console(chat.run_stream(task="Examine bill s1663-115 please."))

if __name__ == "__main__":
    asyncio.run(main())


# selector_prompt = """
# You are the moderator in a conversation that will be used as an investigation to detect a company's interests in different data points about a bill in the United States Congress.
# The following agents are available to play the roles of the participants in the conversation:
# {roles}.

# The following is the conversation history:
# {history}

# Read the above conversation. Then select the next speaker from {participants} to play. Only return the name of the speaker.

# If the conversation is empty, start with the committee_specialist.
# """
# termination_condition = TextMentionTermination("investigation is concluded")