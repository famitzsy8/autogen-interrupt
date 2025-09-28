import asyncio
import os
from pathlib import Path
import configparser

import pytest

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.agents._user_control_agent import UserControlAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(
    os.getenv("ENABLE_OPENAI_INTEGRATION") != "1",
    reason="requires ENABLE_OPENAI_INTEGRATION=1 to run integration test with real OpenAI API",
)
async def test_interrupt_with_real_agents():
    """Test interrupt functionality with real OpenAI agents discussing Chilean politics."""

    secrets_path = Path(__file__).resolve().with_name("secrets.ini")
    config = configparser.ConfigParser()
    if not secrets_path.exists():
        pytest.skip("secrets.ini not found; cannot run integration test")

    config.read(secrets_path)
    try:
        api_key = config["API_KEYS"]["OPENAI_API_KEY"]
    except KeyError:
        pytest.skip("OpenAI API key missing from secrets.ini")

    print("🧪 AutoGen Interrupt Functionality Test")
    print("Testing with real OpenAI agents discussing Chilean politics")
    print("=" * 60)
    
    # Setup OpenAI client
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=api_key,
    )
    
    # Create agents with updated personas
    communist_agent = AssistantAgent(
        name="Jara_Supporter",
        model_client=model_client,
        description="Supporter of Daniel Jadue/left-wing candidate",
        system_message="""You are a passionate supporter of left-wing politics in Chile. You believe in:
- Strong social programs and wealth redistribution
- Workers' rights and labor unions
- Critique of neoliberal capitalism
- Support for candidates like Daniel Jadue or similar left-wing politicians

Keep your responses SHORT (1-2 sentences max). Never say TERMINATE. Reply to the others' comments. Start polite but become more aggressive and witful."""
    )
    
    liberal_agent = AssistantAgent(
        name="Kast_Supporter",
        model_client=model_client,
        description="Supporter of José Antonio Kast/right-wing candidate",
        system_message="""You are a supporter of right-wing/conservative politics in Chile. You believe in:
- Free market capitalism and reduced government intervention
- Traditional values and law and order
- Support for candidates like José Antonio Kast
- Economic growth through private enterprise

Keep your responses SHORT (1-2 sentences max). Never say TERMINATE. Reply to the others' comments. Start polite but become more aggressive and witful."""
    )
    
    # Create team with updated termination condition
    team = RoundRobinGroupChat(
        participants=[communist_agent, liberal_agent],
        termination_condition=MaxMessageTermination(max_messages=10),
    )
    
    # Create user control agent
    user_control = UserControlAgent(name="UserController")
    
    # Run the test
    try:
        print("🚀 Starting Real Agent Interrupt Test")
        print("=" * 60)
        
        conversation_task = asyncio.create_task(
            run_conversation_with_interrupt(team, user_control)
        )
        
        await conversation_task
        
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print(f"💥 Test failed: {e}")
        raise

async def run_conversation_with_interrupt(team, user_control):
    """Run conversation with interrupts and provocations."""
    
    initial_topic = """
Simple debate: Who should win the 2025 Chilean presidential election - a left-wing candidate like Jadue or a right-wing candidate like Kast?

Jara_Supporter: Start by arguing why the left-wing candidate should win. Keep it short!
Kast_Supporter: Then argue why the right-wing candidate is better. Keep it short!

Take turns, one sentence each. NO long explanations!
"""
    
    provocative_messages = [
        "What about the corruption scandals? How do you defend that?",
        "Isn't your candidate just promising things they can't deliver?",
        "Your economic policies failed before - why would they work now?",
    ]
    
    return await run_simple_interrupt_test(team, user_control, initial_topic, provocative_messages)

async def run_simple_interrupt_test(team, user_control, initial_topic, provocative_messages):
    """Test with one continuous stream, interrupting at specific message counts."""
    
    print("🏛️ Starting Chilean Politics Discussion...")
    print("Participants: Jara Supporter vs Kast Supporter")
    print("-" * 40)
    print("ℹ️  Strategy: Use one continuous stream, interrupt every ~10 messages")
    print("-" * 40)
    
    total_message_count = 0
    provocation_index = 0
    next_provocation_at = 5  # First interrupt after 5 messages
    
    # Start one continuous conversation stream
    try:
        stream = team.run_stream(task=initial_topic)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print(f"💥 Test failed: {e}")
        raise
    
    async for message in stream:
        if hasattr(message, 'content') and hasattr(message, 'source'):
            total_message_count += 1
            print(f"[{total_message_count}] [{message.source}]: {message.content}")
            print("-" * 40)
            
            # Check if it's time for a provocation
            if total_message_count >= next_provocation_at and provocation_index < len(provocative_messages) + 1:
                
                if provocation_index == 0:
                    # First interrupt - Pinochet question
                    print(f"\n🛑 FIRST INTERRUPT (after {total_message_count} messages)!")
                    await user_control.interrupt(team)
                    
                    pinochet_question = "Wait! Kast supporter, what about Kast's controversial statements about Pinochet? How do you defend that?"
                    print(f"💬 [USER INTERRUPT]: {pinochet_question}")
                    print("-" * 40)
                    
                    result = await user_control.send(team, pinochet_question, "Kast_Supporter")
                    next_provocation_at = total_message_count + 10  # Next provocation in 10 messages
                    
                else:
                    # Regular provocations
                    provocation = provocative_messages[provocation_index - 1]
                    print(f"\n💥 PROVOCATION #{provocation_index} (after {total_message_count} messages)!")
                    
                    # Alternate targets - start with Jara_Supporter for regular provocations
                    target = "Jara_Supporter" if ((provocation_index - 1) % 2 == 0) else "Kast_Supporter"
                    target_description = "LEFT-WING (Jara)" if target == "Jara_Supporter" else "RIGHT-WING (Kast)"
                    
                    print(f"🎯 TARGET: {target} ({target_description})")
                    print(f"💬 [USER PROVOCATION]: {provocation}")
                    print("-" * 40)
                    
                    await user_control.interrupt(team)
                    result = await user_control.send(team, provocation, target)
                    next_provocation_at = total_message_count + 10  # Next provocation in 10 messages
                
                # Display the response from the provocation
                for msg in result.messages:
                    if hasattr(msg, 'content') and hasattr(msg, 'source') and msg.source != "RoundRobinGroupChatManager":
                        total_message_count += 1
                        print(f"[{total_message_count}] [{msg.source}]: {msg.content}")
                        print("-" * 40)
                
                provocation_index += 1
                print("🔄 Conversation should continue naturally...")
                
        elif hasattr(message, 'stop_reason'):
            print(f"\n🏁 Stream ended: {message.stop_reason}")
            break
        
        # Stop after reasonable number of messages
        if total_message_count >= 30:
            print(f"\n🏁 Reached {total_message_count} messages - ending test")
            break
    
    # Final summary
    print(f"\n🎭 CONVERSATION COMPLETE!")
    print(f"📊 Total messages: {total_message_count}")
    print(f"🔥 Provocations sent: {provocation_index}")
    print("🎯 Target pattern: Pinochet question to Kast, then alternating provocations")
    print("✅ Extended interrupt functionality test completed!")

if __name__ == "__main__":
    asyncio.run(test_interrupt_with_real_agents())
