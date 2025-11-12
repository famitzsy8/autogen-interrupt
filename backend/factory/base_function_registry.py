import importlib
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Dict


@dataclass
class FunctionMetadata:
    name: str
    module: str
    function: Callable
    signature: inspect.Signature
    is_async: bool
    description: str = ""


class BaseFunctionRegistry(ABC):
    def __init__(self):
        self._functions: Dict[str, FunctionMetadata] = {}
        self._load_errors: list[str] = []

    def load_from_module(self, module_path: str):
        # Common discovery logic for all function types
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            error = f"Failed to import {module_path}: {e}"
            self._load_errors.append(error)
            return

        for name, obj in inspect.getmembers(module):
            if name.startswith("_") or not callable(obj):
                continue
            if inspect.getmodule(obj) != module:
                continue

            try:
                metadata = self._validate_and_create_metadata(name, obj, module_path)
                if metadata:
                    self._functions[name] = metadata
            except ValueError as e:
                self._load_errors.append(f"     {name}: {e}")

    @abstractmethod
    def _validate_and_create_metadata(
        self, name: str, func: Callable, module_path: str
    ) -> FunctionMetadata | None:
        # Subclasses implement validation rules specific to their function type
        pass

    def get_function(self, name: str) -> Callable:
        # Retrieve function by name
        if name not in self._functions:
            available = list(self._functions.keys())
            raise KeyError(f"Function '{name}' not found\nAvailable: {available}")
        return self._functions[name].function

    def list_functions(self) -> Dict[str, FunctionMetadata]:
        return dict(self._functions)

    def get_errors(self) -> list[str]:
        return self._load_errors

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(functions={len(self._functions)}, errors={len(self._load_errors)})"
