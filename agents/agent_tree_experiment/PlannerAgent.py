# This is an extension of the autogen.AssistantAgent class that we use to force the model
# to plan ahead before executing a tool call, in order to avoid tool calls with empty arguments

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import (
    UserMessage,
    ToolCallRequestEvent,
    ToolCallExecutionEvent,
)
from autogen_core.models import (
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    AssistantMessage,
)
from autogen_core.models import (
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    AssistantMessage,
)
from autogen_agentchat.messages import UserMessage 
from autogen_agentchat.messages import ToolCallExecutionEvent

import yaml
from util.other_util import _craft_adapted_path

class PlannerAgent(AssistantAgent):
    """
    An AssistantAgent that intercepts the first tool-call attempt after receiving
    a task and forces the model to generate a plan first.
    It works by checking if a model result contains tool calls AND if it's the
    first such attempt in the current turn. If so, it injects a "please plan"
    message and re-runs the model. Subsequent tool calls within the same turn
    are processed normally by the parent AssistantAgent logic.
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
        # Condition to check if this is the very first tool call attempt of the turn.
        is_first_tool_call_attempt = isinstance(model_result.content, list) and not any(
            isinstance(m, (ToolCallRequestEvent, ToolCallExecutionEvent)) for m in inner_messages
        )
        is_attempt_without_arguments = isinstance(model_result.content, list) and any(
            any(call.arguments == "{}" for call in m.content)
            for m in model_result.content if isinstance(m, ToolCallRequestEvent)
        )

        with open(_craft_adapted_path('config/prompt.yaml'), 'r') as file:
            prompt_config = yaml.safe_load(file)

        # If we get back a bill text, committee report, or committee meeting, we need to build a RAG index
        # because the texts are simply too long for the model to process right away
        # Also, it is assumed that the model will be able to better query the contents than it would be able to take
        # all the text information into account at once.
        if isinstance(model_result.content, list):
            for m in model_result.content:
                if isinstance(m, ToolCallExecutionEvent):
                    for function_call in m.content:
                        if not function_call.is_error:
                            if function_call.name in ["extractBillText", "get_committee_report", "get_committee_meeting"]:
                                # implement the RAG pipeline her
                                # something like this:
                                # build_index(function_call.content)
                                pass

        print("\nis_attempt_without_arguments", is_attempt_without_arguments)
        print("\n\nmodel_result.content", model_result.content)
        print("\nis_first_tool_call_attempt", is_first_tool_call_attempt)
        print("\ninner_messages", inner_messages)
        if not is_first_tool_call_attempt or not is_attempt_without_arguments:
            # Not the first tool call, or not a tool call at all. Delegate to parent.
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

        # ---- It IS the first tool call attempt. Enforce planning. ----
        # The parent `on_messages_stream` already added the AssistantMessage for the
        # initial `model_result` to the context before calling this method.

        # 1. Add dummy tool responses to satisfy the OpenAI protocol.
        print("Adding dummy tool responses to satisfy the OpenAI protocol.")
        dummy_results = [
            FunctionExecutionResult(
                content="Plan requested before execution. This tool was not run.",
                call_id=call.id,
                is_error=True,
                name=call.name,
            )
            for call in model_result.content
        ]
        await model_context.add_message(FunctionExecutionResultMessage(content=dummy_results))

        # 2. Inject the "please plan" user message.
        print("Injecting the \"please plan\" user message.")
        await model_context.add_message(
            UserMessage(
                content=prompt_config["planning_prompt"]["description"],
                source="system-enforcer",
            )
        )

        # 3. Re-run the model to get a new response that includes the plan. 
        print("Re-running the model to get a new response that includes the plan.")
        next_model_result: CreateResult | None = None
        async for chunk in cls._call_llm(
            model_client=model_client,
            model_client_stream=model_client_stream,
            system_messages=system_messages,
            model_context=model_context,
            workbench=workbench,
            handoff_tools=handoff_tools,
            agent_name=agent_name,
            cancellation_token=cancellation_token,
            output_content_type=output_content_type,
            message_id=message_id,
        ):
            if isinstance(chunk, CreateResult):
                next_model_result = chunk
            else:
                yield chunk  # Pass streaming chunks through.

        assert next_model_result is not None, "No model result produced after requesting plan."

        # 4. Add the new assistant message (with plan) to the context.
        print("Adding the new assistant message (with plan) to the context.")
        await model_context.add_message(        
            AssistantMessage(
                content=next_model_result.content,
                source=agent_name,
                thought=getattr(next_model_result, "thought", None),
            )
        )

        # 5. Delegate the NEW result back to the parent's processing logic. 
        print("Delegating the NEW result back to the parent's processing logic.")
        async for event in super()._process_model_result(
            next_model_result,
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