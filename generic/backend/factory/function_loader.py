from typing import Callable, List
from factory.registry import FunctionRegistry

class FunctionLoader:

    def __init__(self, registry: FunctionRegistry):
        self.registry = registry
    
    def get_tool_function(self, name: str) -> Callable:
        return self.registry.get_tool_function(name)

    def get_tool_functions_by_names(self, names: List[str]) -> List[Callable]:

        tools = []
        for name in names:
            tool = self.get_tool_function(name)
            tools.append(tool)
        
        return tools
    
    def __repr__(self) -> str:
        return f"FunctionLoader(registry={self.registry})"