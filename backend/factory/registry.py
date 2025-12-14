import inspect
from typing import Callable
from factory.base_function_registry import BaseFunctionRegistry, FunctionMetadata


class FunctionRegistry(BaseFunctionRegistry):
    # Tool function registry - allows sync or async functions with any signature

    def _validate_and_create_metadata(
        self, name: str, func: Callable, module_path: str
    ) -> FunctionMetadata | None:
        # Tool functions: minimal validation, accept sync or async
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or ""

        return FunctionMetadata(
            name=name,
            module=module_path,
            function=func,
            signature=sig,
            is_async=inspect.iscoroutinefunction(func),
            description=doc.split("\n")[0],
        )

    def get_tool_function(self, name: str) -> Callable:
        # Backward compatibility: get_tool_function -> get_function
        return self.get_function(name)

    def get_metadata(self, name: str) -> FunctionMetadata:
        return self._functions[name]

    def list_tools(self):
        return {name: meta.description for name, meta in self._functions.items()}
