#!/usr/bin/env python3
"""
Run the configured investigation task from team.yaml.

This script loads the task configuration from team.yaml and runs it with
the specified company, bill, and year.

Usage:
    python run_investigation.py <company_name> <bill_name> <year>

Example:
    python run_investigation.py "Maersk" "HR 1" "2023"

Or in Docker:
    docker exec -it backend-proxy python run_investigation.py "Maersk" "HR 1" "2023"
"""

import asyncio
import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from factory.team_factory import init_team
from handlers.agent_input_queue import AgentInputQueue
from handlers.state_manager import StateManager
from autogen_agentchat.messages import (
    BaseChatMessage,
    ToolCallRequestEvent,
    ToolCallExecutionEvent,
)


def load_task_from_yaml(company_name: str, bill_name: str, year: str) -> str:
    """Load and format the main task from team.yaml"""

    config_path = Path(__file__).parent / "factory" / "team.yaml"

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    if 'tasks' not in config or 'main_task' not in config['tasks']:
        raise ValueError("No main_task found in team.yaml")

    task_template = config['tasks']['main_task']['description']

    # Replace placeholders
    task = task_template.format(
        company_name=company_name,
        bill_name=bill_name,
        bill=bill_name,  # Some places use {bill} instead of {bill_name}
        year=year
    )

    return task


async def run_investigation(company_name: str, bill_name: str, year: str):
    """Run the investigation task"""

    # Load environment
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment")
        sys.exit(1)

    print("=" * 80)
    print("  Congressional Bill Investigation")
    print("=" * 80)
    print()
    print(f"📊 Investigation Parameters:")
    print(f"   Company: {company_name}")
    print(f"   Bill: {bill_name}")
    print(f"   Year: {year}")
    print()

    # Load task from YAML
    print("📋 Loading investigation task from team.yaml...")
    try:
        task = load_task_from_yaml(company_name, bill_name, year)
    except Exception as e:
        print(f"❌ Failed to load task: {e}")
        sys.exit(1)

    print("✅ Task loaded successfully")
    print()

    # Initialize team
    print("⚙️  Initializing agent team...")
    input_queue = AgentInputQueue()
    state_file = Path(f"/tmp/investigation_{company_name}_{bill_name.replace(' ', '_')}.json")
    _state_manager = StateManager(state_file)

    try:
        context = await init_team(
            api_key=api_key,
            agent_input_queue=input_queue,
            max_messages=150  # Allow long investigation
        )
    except Exception as e:
        print(f"❌ Failed to initialize team: {e}")
        sys.exit(1)

    print(f"✅ Team initialized with {len(context.participant_names)} agents")
    print(f"   Agents: {', '.join(context.participant_names)}")
    print()

    # Show task preview
    print("📄 Investigation Task Preview:")
    print("-" * 80)
    task_lines = task.split('\n')
    for line in task_lines[:10]:  # Show first 10 lines
        print(line)
    if len(task_lines) > 10:
        print(f"... ({len(task_lines) - 10} more lines)")
    print("-" * 80)
    print()

    # Run investigation
    print("🚀 Starting investigation...")
    print()

    stream = context.team.run_stream(task=task)

    message_count = 0
    tool_call_count = 0
    agent_message_counts = {}

    try:
        async for event in stream:
            # Agent messages
            if isinstance(event, BaseChatMessage):
                message_count += 1
                source = getattr(event, 'source', 'Unknown')
                content = str(event.content)

                # Track per-agent message counts
                agent_message_counts[source] = agent_message_counts.get(source, 0) + 1

                # Print agent name
                print(f"\n{'='*60}")
                print(f"[{source}] (Message #{agent_message_counts[source]})")
                print('='*60)

                # Print content (truncate very long messages)
                if len(content) > 1000:
                    print(content[:1000])
                    print(f"\n... (content truncated, {len(content)} chars total)")
                else:
                    print(content)

            # Tool calls
            elif isinstance(event, ToolCallRequestEvent):
                for call in event.content:
                    tool_call_count += 1
                    tool_name = getattr(call, 'name', 'unknown')
                    arguments = str(getattr(call, 'arguments', '{}'))

                    print(f"\n{'─'*60}")
                    print(f"🔧 Tool Call #{tool_call_count}: {tool_name}")

                    # Show arguments
                    if len(arguments) > 300:
                        print(f"   Arguments: {arguments[:300]}...")
                    else:
                        print(f"   Arguments: {arguments}")

            # Tool results
            elif isinstance(event, ToolCallExecutionEvent):
                for result in event.content:
                    content = str(getattr(result, 'content', ''))

                    # Show truncated result
                    if len(content) > 400:
                        print(f"   ✓ Result: {content[:400]}...\n")
                    else:
                        print(f"   ✓ Result: {content}\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Investigation interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during investigation: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print()
    print("=" * 80)
    print("  Investigation Summary")
    print("=" * 80)
    print(f"Total messages: {message_count}")
    print(f"Total tool calls: {tool_call_count}")
    print()
    print("Messages per agent:")
    for agent, count in sorted(agent_message_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {agent}: {count} messages")
    print()
    print("✅ Investigation completed!")
    print()

    # Cleanup
    if state_file.exists():
        state_file.unlink()


def main():
    """Main entry point"""

    # Check arguments
    if len(sys.argv) < 4:
        print("Usage: python run_investigation.py <company_name> <bill_name> <year>")
        print()
        print("Example:")
        print('  python run_investigation.py "Maersk" "HR 1" "2023"')
        print()
        print("Or in Docker:")
        print('  docker exec backend-proxy python run_investigation.py "Maersk" "HR 1" "2023"')
        sys.exit(1)

    company_name = sys.argv[1]
    bill_name = sys.argv[2]
    year = sys.argv[3]

    try:
        asyncio.run(run_investigation(company_name, bill_name, year))
    except KeyboardInterrupt:
        print("\n⚠️  Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
