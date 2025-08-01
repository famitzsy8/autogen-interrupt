import asyncio
import yaml
import logging
from typing import Sequence, List

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage

from util.api_util import __get_api_keys
from util.other_util import _craft_adapted_path

from PlannerAgent import PlannerAgent
from FilteredWorkbench import FilteredWorkbench
from autogen_agentchat.ui import Console

def _append_next_agent_instruction(agents_cfg: dict, agent_names: List[str]) -> None:
    """Mutate the description field of each agent by appending explicit hand-off instructions."""
    addon = (
        "\n\nWhen you want to hand off, finish **your last line** with "
        "'NEXT_AGENT: <agent_name>' where <agent_name> is one of "
        f"{agent_names} or TERMINATE."
    )
    for name in agent_names:
        agents_cfg[name]["description"] += addon

# ASSUMES: agent names are of the form "{agent_name}_{agent_tag}"
def __augment_agent_names(agent_names: List[str]) -> List[str]:
    """
    Creates a list of plausible names an LLM might use for each agent.
    - Handles spaces vs. underscores.
    - Creates "specialist in ..." variants.
    - Handles plurals, using an apostrophe for names already ending in 's' (e.g., actions -> actions').
    """
    new_names = []
    for name in agent_names:
        if name == "orchestrator":
            # Orchestrator is a special case, no augmentation needed.
            continue
        
        fragments = name.split("_")
        core_name, tag = " ".join(fragments[:-1]), fragments[-1]

        # 1. Singular forms
        new_names.append(f"{core_name} {tag}")          # e.g., "committee specialist"
        new_names.append(f"specialist in {core_name}") # e.g., "specialist in committee"

        # 2. Plural forms
        if core_name.endswith('s'):
            # For "actions", becomes "actions'"
            plural_core = core_name + "'"
        else:
            # For "committee", becomes "committees"
            plural_core = core_name + "s"
        
        new_names.append(f"{plural_core} {tag}")         # e.g., "committees specialist", "actions' specialist"
        new_names.append(f"specialist in {plural_core}")# e.g., "specialist in committees", "specialist in actions'"
        
    return list(set(new_names)) # Use set to remove any duplicates


def __deaugment_agent_name(augmented_name: str, canonical_names: List[str]) -> str:
    """
    Takes a potentially augmented agent name (e.g., from model output) and maps it
    back to its canonical form (e.g., 'committee_specialist'). This is the inverse
    of __augment_agent_names.
    """
    if augmented_name in canonical_names:
        return augmented_name

    # Normalize the input: lowercase, strip, handle spaces/underscores.
    normalized_input = augmented_name.lower().strip().replace("_", " ")

    # Iterate through each canonical name and check if any of its augmented forms match.
    for canonical_name in canonical_names:
        if canonical_name == "orchestrator":
            if normalized_input == "orchestrator":
                return "orchestrator"
            continue

        fragments = canonical_name.split("_")
        core_name = " ".join(fragments[:-1])
        tag = fragments[-1]

        # Generate the plural form based on the new augmentation logic.
        if core_name.endswith('s'):
            plural_core = core_name + "'"
        else:
            plural_core = core_name + "s"

        # Generate all possible augmented forms for this canonical name.
        augmented_forms = {
            f"{core_name} {tag}",
            f"specialist in {core_name}",
            f"{plural_core} {tag}",
            f"specialist in {plural_core}",
        }

        if normalized_input in augmented_forms:
            return canonical_name

    raise ValueError(f"Could not de-augment agent name '{augmented_name}' into any of {canonical_names}")

def _check_agent_name_safety(agent_names: List[str]) -> bool:
    """
    Verifies that for every canonical agent name, all its augmented forms can be
    correctly mapped back to the original canonical name.
    """
    for canonical_name in agent_names:
        if canonical_name == "orchestrator":
            continue

        # Re-create the specific augmented forms for this one agent to test them.
        fragments = canonical_name.split("_")
        core_name = " ".join(fragments[:-1])
        tag = fragments[-1]

        if core_name.endswith('s'):
            plural_core = core_name + "'"
        else:
            plural_core = core_name + "s"
        
        augmented_forms = [
            f"{core_name} {tag}",
            f"specialist in {core_name}",
            f"{plural_core} {tag}",
            f"specialist in {plural_core}",
        ]
        
        # Test if each augmented form correctly maps back to the original.
        for augmented_form in augmented_forms:
            try:
                deaugmented_name = __deaugment_agent_name(augmented_form, agent_names)
                if deaugmented_name != canonical_name:
                    print(f"SAFETY CHECK FAILED: '{augmented_form}' de-augmented to '{deaugmented_name}', but expected '{canonical_name}'")
                    return False
            except ValueError as e:
                print(f"SAFETY CHECK FAILED: '{augmented_form}' could not be de-augmented at all. ERROR: {e}")
                return False
                
    return True


def _create_smart_selector(agent_names: List[str]) -> callable:
    """Creates a closure for the selector function that has access to agent names."""

    def _explicit_selector(thread: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
        """
        Look for a directive to hand off to the next agent.

        This function first checks for an explicit, reliable marker: `NEXT_AGENT: <name>`.
        If the marker is not found, it attempts a more lenient search, checking if the
        last line of the message contains a mention of any of the available agents.
        """
        selector_logger.info("-" * 20)
        selector_logger.info("Selector function called.")

        names = __augment_agent_names(agent_names)

        last_msg = next((m for m in reversed(thread) if isinstance(m, BaseChatMessage)), None)

        if not last_msg:
            selector_logger.info("No chat message found in the thread. Fallback to LLM.")
            return None

        txt = getattr(last_msg, "to_text", lambda: last_msg.content)()
        selector_logger.info(f"Analyzing message from '{last_msg.source}': '{txt.strip()}'")

        # 1. Check for agent name mention (case-insensitive, underscore/space flexible).
        last_line = txt.strip()
        selector_logger.info(f"No explicit marker. Analyzing last line for implicit mention: '{last_line}'")

        lower_last_line = last_line.replace("_", " ").lower()
        mentioned_agents = []
        for name in names:
            # Check for forms like "committee_specialist" or "Committee agent"
            name_with_space = name.replace("_", " ").lower()
            if name.lower() in lower_last_line or name_with_space in lower_last_line:
                mentioned_agents.append(name)

        if len(mentioned_agents) == 1:
            selector_logger.info(f"SUCCESS: Found implicit mention of '{mentioned_agents[0]}' in the last line.")
            return __deaugment_agent_name(mentioned_agents[0], agent_names)
        elif len(mentioned_agents) > 1:
            selector_logger.warning(f"Ambiguous: multiple agents {mentioned_agents} mentioned. We select the last one mentioned..")
            return __deaugment_agent_name(mentioned_agents[-1], agent_names)
        else:
            selector_logger.info("No agent mentioned in last line. Fallback to LLM.")

        return None

    return _explicit_selector




# Configure logging: selector debug to file, only warnings to console
logging.getLogger().setLevel(logging.WARNING)  # Set default level to WARNING for all loggers
selector_logger = logging.getLogger("selector")
selector_logger.setLevel(logging.INFO)

# Create file handler for selector logs
file_handler = logging.FileHandler("selector_debug.log", mode="w")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))
selector_logger.addHandler(file_handler)


async def main() -> None:
    # -------------------- Config & constants --------------------
    advancement = "advancement"
    bill = "s1661-115"
    selected_agent_names = ["committee_specialist", "bill_specialist", "orchestrator", "actions_specialist", "amendment_specialist", "congress_member_specialist"]

    # -------------------- Load YAML configs --------------------
    with open(_craft_adapted_path("config/agents.yaml"), "r") as f:
        agents_cfg = yaml.safe_load(f)
    with open(_craft_adapted_path("config/tasks.yaml"), "r") as f:
        tasks_cfg = yaml.safe_load(f)
    with open(_craft_adapted_path("config/prompt.yaml"), "r") as f:
        prompt_cfg = yaml.safe_load(f)

    # Concatenate NEXT_AGENT instructions to each selected agent description
    _append_next_agent_instruction(agents_cfg, selected_agent_names)

    # -------------------- Model client --------------------
    oai_key, _ = __get_api_keys()
    model_client = OpenAIChatCompletionClient(model="gpt-4.1", api_key=oai_key)

    # -------------------- Workbench setup --------------------
    params = StdioServerParams(
        command="python",
        args=["congressMCP/main.py"],
        read_timeout_seconds=60,
    )

    async with McpWorkbench(server_params=params) as workbench:
        allowed_tool_names_comm = ["get_committee_members", "get_committee_actions", "getBillCommittees"]
        allowed_tool_names_bill = ["extractBillText", "getBillSponsors", "getBillCoSponsors", "getBillCommittees"]
        allowed_tool_names_actions = ["extractBillActions", "get_committee_actions"]
        allowed_tool_names_amendments = ["extractAmendmentText", "getAmendmentSponsors", "getAmendmentCoSponsors", "getBillText"]
        allowed_tool_names_congress_members = ["getCongressMemberName", "getCongressMemberParty", "getCongressMemberState", "getBillSponsors", "getBillCoSponsors"]

        workbench_comm = FilteredWorkbench(workbench, allowed_tool_names_comm)
        workbench_bill = FilteredWorkbench(workbench, allowed_tool_names_bill)
        workbench_actions = FilteredWorkbench(workbench, allowed_tool_names_actions)
        workbench_amendments = FilteredWorkbench(workbench, allowed_tool_names_amendments)
        workbench_congress_members = FilteredWorkbench(workbench, allowed_tool_names_congress_members)

        termination_condition = TextMentionTermination("TERMINATE")

        committee_specialist = PlannerAgent(
            name = "committee_specialist",
            description = agents_cfg["committee_specialist"]["description"].format(advancement=advancement, agent_names=selected_agent_names),
            model_client=model_client,
            workbench=workbench_comm,
            model_client_stream=True,
            reflect_on_tool_use=True
        )
        bill_specialist = PlannerAgent(
            name="bill_specialist",
            description=agents_cfg["bill_specialist"]["description"].format(agent_names=selected_agent_names),
            model_client=model_client,
            workbench=workbench_bill,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        actions_specialist = PlannerAgent(
            name="actions_specialist",
            description=agents_cfg["actions_specialist"]["description"].format(agent_names=selected_agent_names),
            model_client=model_client,
            workbench=workbench_actions,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        amendment_specialist = PlannerAgent(
            name="amendment_specialist",
            description=agents_cfg["amendment_specialist"]["description"].format(agent_names=selected_agent_names),
            model_client=model_client,
            workbench=workbench_amendments,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        congress_member_specialist = PlannerAgent(
            name="congress_member_specialist",
            description=agents_cfg["congress_member_specialist"]["description"].format(agent_names=selected_agent_names),
            model_client=model_client,
            workbench=workbench_congress_members,
            model_client_stream=True,
            reflect_on_tool_use=True
        )

        agents = [committee_specialist, bill_specialist, actions_specialist, amendment_specialist, congress_member_specialist]
        agent_names = [agent.name for agent in agents]
        orchestrator = AssistantAgent(
            name="orchestrator",
            description= agents_cfg["orchestrator"]["description"].format(bill=bill, advancement=advancement, agent_names=agent_names),
            model_client=model_client,
            model_client_stream=True,
        )
        agents.append(orchestrator)
        
        # Create the selector function with access to the agent names
        smart_selector = _create_smart_selector(agent_names=[a.name for a in agents])


        # # Test the augment and deaugment functions
        # augmented_names = __augment_agent_names(agent_names)
        # deaugmented_names = {name: __deaugment_agent_name(name, agent_names) for name in augmented_names}
        # print(f"Augmented names: {augmented_names}")
        # print(f"Deeaugmented names: {deaugmented_names}")
        # print(f"All deaugmented names in augmented names: {all(name in deaugmented_names for name in augmented_names)}")

        if not _check_agent_name_safety(agent_names):
            raise ValueError("Agent names are not safe to use in the selector function.")

        team = SelectorGroupChat(
            agents,
            termination_condition=termination_condition,
            selector_func=smart_selector,
            model_client=model_client
        )
        await Console(team.run_stream(task=tasks_cfg["main_task"]["description"].format(bill=bill, advancement=advancement)))

if __name__ == "__main__":
    asyncio.run(main())
