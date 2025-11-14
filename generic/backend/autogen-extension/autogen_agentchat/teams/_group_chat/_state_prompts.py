"""State update prompts for three-state context management.

These prompts are used by SelectorGroupChatManager to update:
- StateOfRun: Research progress and next steps
- ToolCallFacts: Discovered facts from tool executions
- HandoffContext: Agent selection rules and guidelines

All prompts use string templates for .format() calls.
"""

STATE_OF_RUN_UPDATE_PROMPT = """Your task is to update the state of a research process done by a team of agents.

## What you receive

1. The Previous State of the Research -- It outlines what has been done already, and what the next step at the previous point in time was
2. The Message from the Agent -- It outlines what the agent did since the state of the research has been documented

## Previous State of Research

{stateOfRun}

## Message from the Agent

{agentMessage}

## Your Task

Update the state of research according to the agent message you just received. Keep the same structure: Task, What we have done so far, Research Outlook (Next Steps), Concrete Next Step

1. DO NOT EDIT THE TASK
2. Edit What we have done so far by synthesizing the old state with the Message from the Agent
3. Edit the Research Outlook section, by taking out steps that have been already done. NOTE: only add new steps when the agent message explicitly mentions them
4. CHOOSE the concrete next step logically from the Research Outlook section. If it is not clear, write <toInfer>
"""

TOOL_CALL_UPDATING_PROMPT = """Your task is to update the whiteboard where we gather all information that the team of agents found via tools.

## What you receive

1. The Current Whiteboard -- It lists ALL the facts that have been found, together with the agent and the tool call name
2. The Results from the new tool calls -- They may or may not contain new information

## Current Whiteboard

{toolCallFacts}

## New Results

{toolCallExecutionResults}

## Your Task

Output an Updated whiteboard with the same structure (grouped by facts) in the following way:

1. Look at all the existing facts on the whiteboard
2. Look at the facts that the tool call results give
3. Create new facts for each NEW AND NOT PREVIOUSLY LISTED information that the new tool call results give us
"""

HANDOFF_CONTEXT_UPDATING_PROMPT = """Your task is to update the instructions to determine when our agent team should request feedback from the human user running them.

## What you receive

1. Information about the current state of research
2. The previous instructions that determined when to invoke which agent, and when to invoke feedback from the human user
3. The agent name of the human user (e.g. 'User_Proxy')
4. The message received from the human user that addresses changes to the agent invocation logic

## Information about the current state of research

{stateOfRun}

## Previous Handoff Instructions

{handoffContext}

## Name of the Human User Agent

{user_proxy_name}

## Message from the Human User

{user_message}

## Your Task

Output updated handoff instructions in the following manner:

1. Keep the structure of the old handoff instructions (If XY: agent_name, ..., ## Special User Requests)
2. Update the handoff instructions ONLY according to the message from the human user
3. Do NOT remove rules that the user didn't mention changing
"""
