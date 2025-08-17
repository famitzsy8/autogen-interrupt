# This is an extension of the autogen.AssistantAgent class that we use to force the model
# to plan ahead before executing a tool call, in order to avoid tool calls with empty arguments

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import (
    UserMessage,
    ToolCallRequestEvent,
    ToolCallExecutionEvent,
)
from autogen_core import FunctionCall
from autogen_core.models import (
    CreateResult,
)
from autogen_agentchat.messages import UserMessage
from autogen_agentchat.messages import ToolCallExecutionEvent
from FilteredWorkbench import FilteredWorkbench

import yaml
import json
import re
import openai
from util.other_util import _craft_adapted_path
from util.api_util import __get_api_keys as get_api_keys

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
            with open(_craft_adapted_path('config/prompts.yaml'), 'r') as file:
                prompt_config = yaml.safe_load(file) or {}
        except FileNotFoundError:
            try:
                with open(_craft_adapted_path('config/prompt.yaml'), 'r') as file:
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
        oai_key, _ = get_api_keys()
        openai.api_key = oai_key

        # Helper to extract JSON from a string robustly
        def _parse_json_maybe(s: str) -> dict:
            try:
                return json.loads(s)
            except Exception:
                match = re.search(r"\{[\s\S]*\}", s)
                if match:
                    try:
                        return json.loads(match.group(0))
                    except Exception:
                        pass
            return {}

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
            pass
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

                    if sent_arguments == "{}":
                        prompt_text = template.format(
                            tool_name=call.name,
                            last_message=last_message_text,
                            description=description,
                            sent_arguments=sent_arguments,
                        )
                        response = openai.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "You extract STRICT JSON arguments for tools."},
                                {"role": "user", "content": prompt_text},
                            ],
                            temperature=0,
                            max_tokens=200,
                        )
                        content = response.choices[0].message.content
                        args_obj = _parse_json_maybe(content or "")
                        print("FACTUALLY CALLED WITH ARGS: ", args_obj)
                        # Use inferred JSON if valid; otherwise keep original arguments
                        if isinstance(args_obj, dict) and len(args_obj) > 0:
                            call.arguments = json.dumps(args_obj)

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