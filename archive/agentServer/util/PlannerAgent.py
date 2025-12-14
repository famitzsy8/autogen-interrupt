# This is an extension of the autogen.AssistantAgent class that we use to force the model
# to plan ahead before executing a tool call, in order to avoid tool calls with empty arguments

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import (
    ToolCallRequestEvent,
)
from autogen_core import FunctionCall
from autogen_core.models import (
    CreateResult,
)

import yaml
import json
import re
import openai
from util.config import _get_key
import os

local_path = os.path.dirname(os.path.abspath(__file__))

class PlannerAgent(AssistantAgent):
    """
    An AssistantAgent that intercepts ANY tool-call request with empty arguments,
    infers the correct arguments using an LLM prompt (gpt-4o) defined in
    `config/prompt.yaml` under the key `arguments_prompt`, and proceeds with the
    original tool call using the inferred JSON arguments.
    """

    @classmethod
    async def _process_model_result(
        cls,
        model_result: CreateResult,
        inner_messages: list,
        cancellation_token,
        agent_name,
        system_messages,
        model_context,
        workbench,
        handoff_tools,
        handoffs,
        model_client,
        model_client_stream,
        reflect_on_tool_use,
        tool_call_summary_format,
        tool_call_summary_formatter,
        max_tool_iterations,
        output_content_type,
        message_id,
        format_string=None,
    ):
        # Load prompts; prefer config/prompts.yaml if present; fallback to config/prompt.yaml
        prompt_config = {}
        try:
            with open((f"{local_path}/config/prompts.yaml"), 'r') as file:
                prompt_config = yaml.safe_load(file) or {}
        except FileNotFoundError:
            try:
                with open((f"{local_path}/config/prompt.yaml"), 'r') as file:
                    prompt_config = yaml.safe_load(file) or {}
            except FileNotFoundError:
                prompt_config = {}

        # Proceed only if there are tool calls; handle both wrappers and raw FunctionCall objects
        has_tool_calls = isinstance(model_result.content, list) and any(
            isinstance(evt, ToolCallRequestEvent) or isinstance(evt, FunctionCall)
            for evt in model_result.content
        )
        if not has_tool_calls:
            async for event in super()._process_model_result(
                model_result,
                inner_messages,
                cancellation_token,
                agent_name,
                system_messages,
                model_context,
                workbench,
                handoff_tools,
                handoffs,
                model_client,
                model_client_stream,
                reflect_on_tool_use,
                tool_call_summary_format,
                tool_call_summary_formatter,
                max_tool_iterations,
                output_content_type,
                message_id,
                format_string,
            ):
                yield event
            return

        # Extract last message from the last other agent
        async def _get_last_other_message_text() -> str:
            try:
                msgs = await model_context.get_messages()
            except Exception:
                return ""
            for msg in reversed(msgs):
                src = getattr(msg, "source", None)
                content = getattr(msg, "content", None)
                if isinstance(content, str) and src and src != agent_name:
                    return content
            return ""

        last_message_text = await _get_last_other_message_text()

        # Prepare OpenAI client
        oai_key = _get_key("OPENAI_API_KEY")
        openai.api_key = oai_key

        # Helper to extract JSON from a string robustly
        def _parse_json_maybe(s: str) -> dict:
            """
            Attempts to parse a string as JSON. If that fails, tries to extract the first outermost JSON object from the string.
            Returns a dict if possible, else {}.
            """
            if isinstance(s, dict):
                return s
            if not isinstance(s, str):
                return {}
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
            # Find all OUTERMOST {...} blocks in the string
            stack = []
            blocks = []
            start = None
            for i, c in enumerate(s):
                if c == '{':
                    if not stack:
                        start = i
                    stack.append('{')
                elif c == '}':
                    if stack:
                        stack.pop()
                        if not stack and start is not None:
                            blocks.append(s[start:i+1])
                            start = None
            # Try to parse each outermost block, return the first valid dict
            for block in blocks:
                # Replace single quotes with double quotes for JSON compatibility
                block_fixed = block.replace("'", '"')
                try:
                    obj = json.loads(block_fixed)
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    continue
            return {}

        def _json_structures_equal(a, b):
            """
            Recursively compare the structure of two JSON objects (dicts/lists).
            Structure is equal iff:
              - Both are dicts with the same keys, and all values have equal structure
              - Both are lists of the same length, and all elements have equal structure
              - Both are not dict/list (i.e., primitives), then structure is equal

            This function expects both arguments to be Python objects (not strings).
            If you have a string, use _parse_json_maybe(string) to convert it first.
            """
            if isinstance(a, dict) and isinstance(b, dict):
                if set(a.keys()) != set(b.keys()):
                    return False
                for k in a:
                    if not _json_structures_equal(a[k], b[k]):
                        return False
                return True
            elif isinstance(a, list) and isinstance(b, list):
                if len(a) != len(b):
                    return False
                for i in range(len(a)):
                    if not _json_structures_equal(a[i], b[i]):
                        return False
                return True
            else:
                # For primitives, structure is considered equal
                return True


        # Build prompt template
        template = (
            (prompt_config.get("arguments_prompt", {}) or {}).get("description")
            or "Given the last message: \n\n{last_message}\n\n"
               "Infer the JSON arguments for the tool `{tool_name}`. Return ONLY the JSON object with the arguments."
        )

        # Build a lookup of tool descriptions from the workbench (if provided)
        tool_descriptions: dict[str, str] = {}
        try:
            if workbench is not None and hasattr(workbench[0], "list_tools"):
                tools = await workbench[0].list_tools()  # type: ignore[reportUnknownArgumentType]
                for t in tools:
                    # Support both dict-like and attribute-like access
                    name = t["name"] if isinstance(t, dict) else getattr(t, "name", None)
                    desc = t.get("description", "") if isinstance(t, dict) else getattr(t, "description", "")
                    if name:
                        tool_descriptions[name] = desc or ""
        except Exception as e:
            print(f"Error listing tools: {e}")
            # If listing tools fails, proceed without descriptions
            pass

        # Mutate every tool call arguments using LLM inference (regardless of being empty or not)
        if isinstance(model_result.content, list):
            for evt in model_result.content:
                # 1) Wrapped batch of calls
                if isinstance(evt, ToolCallRequestEvent):
                    calls_iter = evt.content
                # 2) Single raw FunctionCall
                elif isinstance(evt, FunctionCall):
                    calls_iter = [evt]
                else:
                    continue

                for call in calls_iter:
                    description = tool_descriptions.get(call.name, "")
                    # Normalize sent arguments to a JSON string for the prompt
                    if isinstance(call.arguments, str) and call.arguments.strip() != "":
                        sent_arguments = call.arguments
                    elif isinstance(call.arguments, dict):
                        sent_arguments = json.dumps(call.arguments)
                    else:
                        sent_arguments = "{}"

                    description_args = _parse_json_maybe(description)
                    sent_arguments = _parse_json_maybe(sent_arguments)
                    if sent_arguments == {} or not _json_structures_equal(sent_arguments, description_args):
                        correct_args = False
                        count = 0
                        while not correct_args and count < 3:
                            warning = "YOU HAVE OUTPUT THE EXAMPLE DICT, READ THE PROMPT AGAIN" if count > 0 else ""
                            prompt_text = template.format(
                                warning=warning,
                                tool_name=call.name,
                                last_message=last_message_text,
                                description=description_args,
                                sent_arguments=sent_arguments,
                            )
                            response = openai.chat.completions.create(
                                model="gpt-5-mini",
                                messages=[
                                    {"role": "system", "content": "You extract STRICT JSON arguments for tools."},
                                    {"role": "user", "content": prompt_text},
                                ],
                            )
                            content = response.choices[0].message.content
                            args_obj = _parse_json_maybe(content or "")
                            
                            print("FACTUALLY CALLED WITH ARGS: ", args_obj)
                            # Use inferred JSON if valid; otherwise keep original arguments
                            if isinstance(args_obj, dict) and len(args_obj) > 0:
                                call.arguments = json.dumps(args_obj)
                            if description_args != args_obj:
                                correct_args = True
                            print("example dict output: ", description_args, args_obj)
                            count += 1

        # Delegate to parent with updated arguments
        async for event in super()._process_model_result(
            model_result,
            inner_messages,
            cancellation_token,
            agent_name,
            system_messages,
            model_context,
            workbench,
            handoff_tools,
            handoffs,
            model_client,
            model_client_stream,
            reflect_on_tool_use,
            tool_call_summary_format,
            tool_call_summary_formatter,
            max_tool_iterations,
            output_content_type,
            message_id,
            format_string,
        ):
            yield event