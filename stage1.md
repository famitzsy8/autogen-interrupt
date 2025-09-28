# Autogen Interrupt: Stage 1

The goal of this repository is to build an extension to Autogen Agentchat, which consists of a UserControlAgent.

## UserControlAgent

The UserControlAgent is an agent that should represent a human user inside of a team of ai agents. Unlike the UserProxyAgent, which is dependent on the team's decision when to call in the human for feedback, the UserControlAgent can send the following signals to the agent team:

### The USER_INTERRUPT signal

The USER_INTERRUPT signal suspends all current activity of the agents and saves the message history and keeps the team intact for a future pick-up of the conversation.

### The USER_MESSAGE signal

The USER_MESSAGE signal is accpeted by the team only after a USER_INTERRUPT signal. It is accompanied by a tuple (MSG, AGENT) that the human user sends into the team, determining his or her message to a specific agent of the team. The groupchatmanager then automatically selects the requested agent AGENT and the team continues with the same message history.

## Your Task

Your task is to go very deep into the autogen library and come up with a plan that details:

- the new objects that need to be created
- the existing autogen objects that the new objects extend
- the ontology of the signals inside autogen
- where these signals arise and where they could get handled or more specifically...
- the needed functions that need to be overwritten, where the signal handling logic will be implemented

### How to Achieve That

1. Create a new virtual environment called `interrupt-cursor-venv`
2. Activate the venv
3. Download autogen_core, autogen_ext and autogen_agentchat with pip. Make sure they are of the version 0.7.4 (the newest one)
4. Browse the autogen library files
4.1 Look into the delegation handling, tool call handling and the message history handling in detail
4.2 Craft a detailed plan according to the section ("Your Task") above


## Output Format

Output your detailed plan into a nicely structured Markdown file that marks code in seperate lines if it is too long

I will then write you a feedback on your plan such that we can craft Stage 2 together.