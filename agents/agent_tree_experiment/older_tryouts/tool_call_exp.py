# This file was used to experiment the ability of different models to call the tools with the
# right arguments

# The results are documented in my log of July 28th

import asyncio

from autogen_core.models import (
    SystemMessage,
    UserMessage,
)

from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from autogen_ext.models.openai import OpenAIChatCompletionClient
from util.api_util import __get_api_keys
import asyncio
from typing import List, Mapping, Any
from autogen_core.tools import ToolSchema, ToolResult
from test_messages import get_messages

class FilteredWorkbench(McpWorkbench):
    """
    A workbench that wraps an existing McpWorkbench to provide a filtered-down
    set of tools to an agent. It also corrects malformed arguments from the agent.
    """

    def __init__(self, underlying_workbench: McpWorkbench, allowed_tool_names: List[str]):
        self._underlying = underlying_workbench
        self._allowed_names = set(allowed_tool_names)
        super().__init__(server_params=self._underlying.server_params)

    async def list_tools(self) -> List[ToolSchema]:
        """Returns only the tools that are in the allowed list."""
        all_tools = await self._underlying.list_tools()
        return [tool for tool in all_tools if tool["name"] in self._allowed_names and tool["description"]]

    async def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None, **kwargs) -> ToolResult:
        """
        Calls the tool only if it's in the allowed list.
        It intercepts the arguments and corrects them before sending them to the server.
        """
        if name not in self._allowed_names:
            raise ValueError(f"Tool '{name}' is not available to this agent.")

        args_to_send = arguments or {}

        return await self._underlying.call_tool(name, args_to_send, **kwargs)

    def _to_config(self) -> Mapping[str, Any]:
        raise NotImplementedError("FilteredWorkbench is not designed to be serializable.")

    @classmethod
    def _from_config(cls, config: Mapping[str, Any]) -> "FilteredWorkbench":
        raise NotImplementedError("FilteredWorkbench is not designed to be serializable.")

class ToolCallExperiment():

    def __init__(self, model_client: OpenAIChatCompletionClient, message:str):
        self.model_client = model_client
        self.message = message

        self.allowed_tool_names_comm = ["get_committee_members", "getBillCommittees", "get_committee_meeting", "get_committee_report"]
        self.allowed_tool_names_bill = ["extractBillText", "getBillSponsors", "getBillCoSponsors"]
        self.allowed_tool_names_actions = ["extractBillActions"]

        # TODO: make this a parameter
        self.params = StdioServerParams(
            command="python",
            args=["congressMCP/main.py"],
            read_timeout_seconds=60,
        )

    async def run(self):
        async with McpWorkbench(server_params=self.params) as workbench:
            workbench_comm = FilteredWorkbench(workbench, self.allowed_tool_names_comm)
            workbench_bill = FilteredWorkbench(workbench, self.allowed_tool_names_bill)
            workbench_actions = FilteredWorkbench(workbench, self.allowed_tool_names_actions)
            
            # Generate a response using the tool.
            comm_tools = await workbench_comm.list_tools()
            response1 = await self.model_client.create(
                messages=[
                    SystemMessage(content="Decide which tools to call in order to get what the user is asking for."),
                    UserMessage(content=f"{self.message}", source="user"),
                ],
                tools=comm_tools,
            )
            print(response1.content)


async def main() -> None:

    openai_models = ["gpt-4o", "gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4.1"]
    messages = get_messages()
    oai_key, _ = __get_api_keys()

    print("RUNNING EXPERIMENT\n\n")
    for model in openai_models:
        model_client = OpenAIChatCompletionClient(
            model=model,
            api_key=oai_key
        )
        for msg_name, msg in messages.items():
            print(f"Running experiment with model {model} and message {msg_name}")
            tool_call_experiment = ToolCallExperiment(model_client, msg)
            await tool_call_experiment.run()
        await model_client.close()

asyncio.run(main())
