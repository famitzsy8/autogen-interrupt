from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass
import importlib
import inspect

@dataclass
class FunctionMetadata:
    # Metadata about a registered function to help the agent choose it
    name: str
    module: str
    function: Callable
    signature: inspect.Signature
    is_async: bool
    description: str = ""


class FunctionRegistry:
    # Thread-safe function registry with validation

    def __init__(self):
        self._tools: Dict[str, FunctionMetadata] = {}
        self._load_errors: list[str] = []

    def load_from_module(self, module_path: str):

        # This function loads all the functions from a module
        try:
            module = importlib.import_module(module_path)
        
        except ImportError as e:

            error = f"Failed to import {module_path}: {e}"
            self._load_errors.append(error)
            return
        
        for name, obj in inspect.getmembers(module):

            # no private functions
            if name.startswith("_"):
                continue

            # no objects that are non-callable
            if not callable(obj):
                continue
            
            # no objects that got imported from other modules
            if inspect.getmodule(obj) != module:
                continue
                
            try:

                metadata = self._create_metadata(name, obj, module_path)
                self._tools[name] = metadata
                
            
            except ValueError as e:
                self._load_errors.append(f"     {name}: {e}")

    def _create_metadata(self, name: str, func: Callable, module_path: str) -> FunctionMetadata:

        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or ""

        return FunctionMetadata(
            name=name,
            module=module_path,
            function=func,
            signature=sig,
            is_async=inspect.iscoroutinefunction(func),
            description=doc.split("\n")[0] # only the first line of the docstring
        )



    def get_tool_function(self, name: str) -> Callable:

        if name not in self._tools:
            available = list(self._tools.keys())
            raise KeyError(
                f"Tool function {name} not found\n"
                f"Available functions are: {available}"
            )
        
        return self._tools[name].function
    
    def get_metadata(self, name: str) -> FunctionMetadata:
        return self._tools[name]
    
    def list_tools(self):
        return {name: meta.description for name, meta in self._tools.items()}

    def get_errors(self):

        return self._load_errors
    
    def __repr__(self) -> str:
        return (
            f"FunctionRegistry("
            f"tools={len(self._tools)}, "
            f"errors={len(self._load_errors)})"
        )
