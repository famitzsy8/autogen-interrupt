# Autogen Interrupt

This is a repository that harbors the autogen extension for human user interruption, as well as some examples of its application.

## Autogen Extension: UserControlAgent

We introduce an extension to the existing Microsoft autogen library (version 0.7.4), that allows a human user to interrupt the entire conversation calling the `interrupt()` function, as well as sending a message to the entire agent team after interrupting.

The extended autogen library can be found in the autogen-extension folder, extending/modifying the `autogen_core` and the `autogen_agentchat` packages. When cloning this repository, run `bash setup.sh` to install the requirements and replace the current autogen packages with our extended versions. 

When editing the extension, call `bash update.sh` in order to transfer the edits into the `autogen-extension` directory.

## Usage Examples

There are three repositories, each containing one usage example for the user interruption. Note that all of these applications run through the CLI.

### Example 1: Simple Political Debate (Trivial)

This is an example of 5 agents with different political leanings discussing Chilean politics. The human user can interrupt upon writing "i" + Enter, and can then send a message to a specific agent.

These examples live in the `/simple_debate` directory. `interrupt_cli.py` is the main working example.

### Example 2: Deep Research (General Purpose)

This is an example of a team of agents, that allows one to do research with web search, and code execution. Currently it is hard-coded in the CLI to fetch information about the CogMaster in Paris but this can be simply modified.

These examples live in the `/deepresearch` directory. `dr_cli_interrupt.py` is the main working example.

### Example 3: Congress Lobbying (Domain-Specific)

This example is the most involved one since it includes an MCP server that allows it to browse the data from the US Congress efficiently. It is still inside a docker container, and there are currently no trivially runneable example (inside `congress-example`)

## Setup

1. Enter the venv

`source interrupt-cursor-venv/bin/activate`

2. Run the setup.sh file

`bash setup.sh`

3. Run one of the files with python

`python xyz_cli.py`

