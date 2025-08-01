# Agent Tree Experiment

This is a collection of tryout files, some more elaborate and some less in order to work with the `autogen-agentchat` library to create a team of agents that work together in a brainstorming-like fashion to find out everything possible about a Congress bill.

### Autogen 1

This is the first comprehensive and working multi-agent system I came up with. It includes 3 agents
working together with an orchestrator and an LLM deciding who the next speaker is.

This version has issues with correct tool calling (which gave rise to `older_tryouts/tool_call_exp`) and correct delegation from one agent to the next.

### Autogen 2

An extension of Autogen 1 with the difference that there are 2 more agents. The same issues remain.

### Autogen 3

A good upgrade to Autogen 2 that includes logic for more correct tool calling (`PlannerAgent`) and complex selection logic to determine the next agent manually instead of an LLM.

### Other Subdirectories

In `older_tryouts/` you will see the first runs I did to understand the library. They are included in this repository for documentation purposes

In `config/` you can find the agents' instructions, tasks and prompts

In `util/` you find all the helper functions to make the codebase a bit neater