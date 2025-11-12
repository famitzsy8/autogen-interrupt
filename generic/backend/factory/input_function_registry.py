import inspect
from typing import Callable
from factory.base_function_registry import BaseFunctionRegistry, FunctionMetadata


class InputFunctionRegistry(BaseFunctionRegistry):
    # Input function registry - strict validation: must be async

    def _validate_and_create_metadata(
        self, name: str, func: Callable, module_path: str
    ) -> FunctionMetadata | None:
        # Input functions must be async
        if not inspect.iscoroutinefunction(func):
            raise ValueError(f"Input function must be async (got {name})")

        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or ""

        return FunctionMetadata(
            name=name,
            module=module_path,
            function=func,
            signature=sig,
            is_async=True,
            description=doc.split("\n")[0],
        )

    def get_input_function(self, name: str) -> Callable:
        # Get input function template by name
        return self.get_function(name)

    def get_metadata(self, name: str) -> FunctionMetadata:
        return self._functions[name]

    def list_input_functions(self):
        return {name: meta.description for name, meta in self._functions.items()}
