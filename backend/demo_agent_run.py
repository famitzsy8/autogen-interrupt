#!/usr/bin/env python3
"""
Demo script to see the agents in action.

This script demonstrates the multi-agent system with real tool calls to the MCP server.
You can watch the agents collaborate to analyze a Congressional bill.

Usage:
    python demo_agent_run.py

Or in Docker:
    docker exec -it backend_server python demo_agent_run.py
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from factory.team_factory import init_team
from handlers.agent_input_queue import AgentInputQueue
from handlers.state_manager import StateManager
from autogen_agentchat.messages import (
    BaseChatMessage,
    ToolCallRequestEvent,
    ToolCallExecutionEvent,
    ToolCallSummaryMessage,
)


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_banner():
    """Print a welcome banner"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}  Multi-Agent Congressional Bill Analysis Demo{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}\n")


def print_section(title: str):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}▶ {title}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'-'*60}{Colors.ENDC}")


def print_agent_message(agent_name: str, message: str):
    """Print an agent's message"""
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}[{agent_name}]{Colors.ENDC}")
    print(f"{Colors.OKGREEN}{message}{Colors.ENDC}")


def print_tool_call(tool_name: str, arguments: str):
    """Print a tool call"""
    print(f"\n{Colors.WARNING}{Colors.BOLD}🔧 Tool Call: {tool_name}{Colors.ENDC}")
    print(f"{Colors.WARNING}   Arguments: {arguments}{Colors.ENDC}")


def print_tool_result(content: str):
    """Print a tool result"""
    # Truncate long results
    if len(content) > 200:
        content = content[:200] + "..."
    print(f"{Colors.OKCYAN}   Result: {content}{Colors.ENDC}")


async def run_demo():
    """Run the agent demo"""

    # Load environment variables
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print(f"{Colors.FAIL}Error: OPENAI_API_KEY not found in environment{Colors.ENDC}")
        print("Please set it in your .env file or export it in your shell.")
        sys.exit(1)

    print_banner()

    print(f"{Colors.BOLD}Initializing multi-agent team...{Colors.ENDC}")

    # Setup
    input_queue = AgentInputQueue()
    state_file = Path("/tmp/demo_state.json")
    _state_manager = StateManager(state_file)  # Initialize state manager

    # Initialize team
    try:
        context = await init_team(
            api_key=api_key,
            agent_input_queue=input_queue,
            max_messages=20  # Allow reasonable conversation
        )
    except Exception as e:
        print(f"{Colors.FAIL}Failed to initialize team: {e}{Colors.ENDC}")
        sys.exit(1)

    print(f"{Colors.OKGREEN}✓ Team initialized with {len(context.participant_names)} agents{Colors.ENDC}")
    print(f"{Colors.OKGREEN}  Agents: {', '.join(context.participant_names)}{Colors.ENDC}")

    print_section("Demo Scenarios")
    print("\nChoose a demo scenario:")
    print(f"{Colors.BOLD}1.{Colors.ENDC} Simple Bill Lookup (HR 1, 118th Congress)")
    print(f"{Colors.BOLD}2.{Colors.ENDC} Bill Analysis with Sponsors and Committees")
    print(f"{Colors.BOLD}3.{Colors.ENDC} Congress Member Research")
    print(f"{Colors.BOLD}4.{Colors.ENDC} Custom Query (enter your own)")

    choice = input(f"\n{Colors.BOLD}Enter choice (1-4): {Colors.ENDC}").strip()

    # Define tasks
    tasks = {
        "1": {
            "title": "Simple Bill Lookup",
            "task": "Get basic information about bill HR 1 from the 118th Congress. Use the getBillSponsors tool."
        },
        "2": {
            "title": "Bill Analysis",
            "task": """Analyze bill S 1 from the 117th Congress.
            I need to know:
            1. Who sponsored it?
            2. Who are the cosponsors?
            3. Which committees is it assigned to?
            Use the appropriate tools to gather this information."""
        },
        "3": {
            "title": "Congress Member Research",
            "task": """Find all Congress members from California (CA) using the getCongressMembersByState tool.
            Then tell me about the first member in the list."""
        }
    }

    if choice not in tasks and choice != "4":
        choice = "1"  # Default

    # Handle custom query separately
    if choice == "4":
        custom_query = input(f"\n{Colors.BOLD}Enter your query: {Colors.ENDC}").strip()
        selected = {
            "title": "Custom Query",
            "task": custom_query
        }
    else:
        selected = tasks[choice]

    print_section(f"Running: {selected['title']}")
    print(f"\n{Colors.BOLD}Task:{Colors.ENDC} {selected['task']}\n")

    # Run the task
    print(f"{Colors.BOLD}Starting agent conversation...{Colors.ENDC}\n")

    stream = context.team.run_stream(task=selected['task'])

    message_count = 0
    tool_call_count = 0

    try:
        async for event in stream:
            # Agent messages
            if isinstance(event, BaseChatMessage):
                message_count += 1
                source = getattr(event, 'source', 'Unknown')
                content = str(event.content)

                # Don't print extremely long messages
                if len(content) > 500:
                    content = content[:500] + f"... ({len(content)} chars total)"

                print_agent_message(source, content)

            # Tool calls
            elif isinstance(event, ToolCallRequestEvent):
                for call in event.content:
                    tool_call_count += 1
                    tool_name = getattr(call, 'name', 'unknown')
                    arguments = str(getattr(call, 'arguments', '{}'))

                    # Truncate long arguments
                    if len(arguments) > 100:
                        arguments = arguments[:100] + "..."

                    print_tool_call(tool_name, arguments)

            # Tool results
            elif isinstance(event, ToolCallExecutionEvent):
                for result in event.content:
                    content = str(getattr(result, 'content', ''))
                    print_tool_result(content)

            # Tool summaries
            elif isinstance(event, ToolCallSummaryMessage):
                content = str(event.content)
                if len(content) > 300:
                    content = content[:300] + "..."
                print(f"\n{Colors.OKCYAN}📋 Summary: {content}{Colors.ENDC}")

    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Demo interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n\n{Colors.FAIL}Error during execution: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()

    # Summary
    print_section("Demo Summary")
    print(f"{Colors.BOLD}Messages exchanged:{Colors.ENDC} {message_count}")
    print(f"{Colors.BOLD}Tool calls made:{Colors.ENDC} {tool_call_count}")

    print(f"\n{Colors.BOLD}{Colors.OKGREEN}Demo completed!{Colors.ENDC}\n")

    # Cleanup
    if state_file.exists():
        state_file.unlink()


def main():
    """Main entry point"""
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Exiting...{Colors.ENDC}")
        sys.exit(0)


if __name__ == "__main__":
    main()
