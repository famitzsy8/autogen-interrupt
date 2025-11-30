# This is the MCP tool workbench that we can use to filter the tools an agent can use
# in the beginning, at the agent's conception

from autogen_ext.tools.mcp import McpWorkbench
from typing import List, Mapping, Any
from autogen_core.tools import ToolSchema, ToolResult

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


