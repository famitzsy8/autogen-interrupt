from typing import Callable
from factory.input_function_registry import InputFunctionRegistry


class InputFunctionLoader:
    # Simple pass-through to InputFunctionRegistry for dependency injection

    def __init__(self, registry: InputFunctionRegistry):
        self.registry = registry

    def get_input_function(self, name: str) -> Callable:
        return self.registry.get_input_function(name)

    def __repr__(self) -> str:
        return f"InputFunctionLoader(registry={self.registry})"
