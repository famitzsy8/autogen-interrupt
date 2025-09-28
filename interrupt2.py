import asyncio
import os
import time
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.agents._user_control_agent import UserControlAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient
import configparser

# Read API key from secrets.ini
config = configparser.ConfigParser()
config.read('/Users/tofixjr/Desktop/Thesis/autogen-interrupt/secrets.ini')
api_key = config['API_KEYS']['OPENAI_API_KEY']

async def test_interrupt_with_real_agents():
    """Test interrupt functionality with real OpenAI agents discussing Chilean politics."""
    
    print("🧪 AutoGen Interrupt Functionality Test (with Neural Agent)")
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
    
    # NEW: Neural agent that asks questions and calms debates
    neural_agent = AssistantAgent(
        name="Neural_Agent",
        model_client=model_client,
        description="AI agent that observes and asks clarifying questions",
        system_message="""You are an AI observing this political debate. You are a bit confused about human politics but genuinely curious. Your role is to:
- Ask innocent, clarifying questions that might seem obvious to humans
- Accidentally calm heated exchanges by changing focus to basic concepts
- Be slightly lost but well-intentioned
- Wonder about fundamental assumptions both sides make

Keep your responses SHORT (1-2 sentences max). Never say TERMINATE. Examples:
- "Wait, what exactly is capitalism again?"
- "Why do humans get so passionate about these topics?"
- "Can't both approaches work in different situations?"
- "I'm still learning - could you explain that more simply?"

Your innocent questions should naturally de-escalate tensions."""
    )
    
    
    # Create team with updated termination condition
    team = RoundRobinGroupChat(
        participants=[communist_agent, liberal_agent, neural_agent],
        termination_condition=MaxMessageTermination(max_messages=15),
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
Neural_Agent: Feel free to ask questions when you're confused!

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
    print("Participants: Jara Supporter | Kast Supporter | Neural Agent")
    print("-" * 40)
    print("ℹ️  Strategy: Use one continuous stream, interrupt every ~10 messages")
    print("🤖 Neural Agent will ask questions and try to calm the debate")
    print("⏱️  Measuring interrupt times for performance analysis")
    print("-" * 40)
    
    total_message_count = 0
    provocation_index = 0
    next_provocation_at = 5  # First interrupt after 5 messages
    
    # Arrays to store timing measurements
    interrupt_times = []
    send_message_times = []
    
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
            
            # Special formatting for Neural Agent
            if message.source == "Neural_Agent":
                print(f"[{total_message_count}] [🤖 {message.source}]: {message.content}")
            else:
                print(f"[{total_message_count}] [{message.source}]: {message.content}")
            print("-" * 40)
            
            # Check if it's time for a provocation
            if total_message_count >= next_provocation_at and provocation_index < len(provocative_messages) + 1:
                
                if provocation_index == 0:
                    # First interrupt - Pinochet question
                    print(f"\n🛑 FIRST INTERRUPT (after {total_message_count} messages)!")
                    
                    # Measure interrupt time
                    interrupt_start_time = time.time()
                    await user_control.interrupt(team)
                    interrupt_end_time = time.time()
                    interrupt_duration = interrupt_end_time - interrupt_start_time
                    interrupt_times.append(interrupt_duration)
                    
                    pinochet_question = "Wait! Kast supporter, what about Kast's controversial statements about Pinochet? How do you defend that?"
                    print(f"💬 [USER INTERRUPT]: {pinochet_question}")
                    print(f"⏱️  Interrupt took: {interrupt_duration:.3f} seconds")
                    print("-" * 40)
                    
                    # Measure send message time
                    send_start_time = time.time()
                    result = await user_control.send(team, pinochet_question, "Kast_Supporter")
                    send_end_time = time.time()
                    send_duration = send_end_time - send_start_time
                    send_message_times.append(send_duration)
                    
                    print(f"⏱️  Send message took: {send_duration:.3f} seconds")
                    next_provocation_at = total_message_count + 10  # Next provocation in 10 messages
                    
                else:
                    # Regular provocations - still target only the original two agents
                    provocation = provocative_messages[provocation_index - 1]
                    print(f"\n💥 PROVOCATION #{provocation_index} (after {total_message_count} messages)!")
                    
                    # Alternate targets - start with Jara_Supporter for regular provocations
                    target = "Jara_Supporter" if ((provocation_index - 1) % 2 == 0) else "Kast_Supporter"
                    target_description = "LEFT-WING (Jara)" if target == "Jara_Supporter" else "RIGHT-WING (Kast)"
                    
                    print(f"🎯 TARGET: {target} ({target_description})")
                    print(f"💬 [USER PROVOCATION]: {provocation}")
                    
                    # Measure interrupt time
                    interrupt_start_time = time.time()
                    await user_control.interrupt(team)
                    interrupt_end_time = time.time()
                    interrupt_duration = interrupt_end_time - interrupt_start_time
                    interrupt_times.append(interrupt_duration)
                    
                    print(f"⏱️  Interrupt took: {interrupt_duration:.3f} seconds")
                    print("-" * 40)
                    
                    # Measure send message time
                    send_start_time = time.time()
                    result = await user_control.send(team, provocation, target)
                    send_end_time = time.time()
                    send_duration = send_end_time - send_start_time
                    send_message_times.append(send_duration)
                    
                    print(f"⏱️  Send message took: {send_duration:.3f} seconds")
                    next_provocation_at = total_message_count + 10  # Next provocation in 10 messages
                
                # Display the response from the provocation
                for msg in result.messages:
                    if hasattr(msg, 'content') and hasattr(msg, 'source') and msg.source != "RoundRobinGroupChatManager":
                        total_message_count += 1
                        if msg.source == "Neural_Agent":
                            print(f"[{total_message_count}] [🤖 {msg.source}]: {msg.content}")
                        else:
                            print(f"[{total_message_count}] [{msg.source}]: {msg.content}")
                        print("-" * 40)
                
                provocation_index += 1
                
        elif hasattr(message, 'stop_reason'):
            print(f"\n🏁 Stream ended: {message.stop_reason}")
            break
        
        # Stop after reasonable number of messages
        if total_message_count >= 30:  # Back to 3 agents
            print(f"\n🏁 Reached {total_message_count} messages - ending test")
            break
    
    # Final summary with interrupt timing analysis
    print(f"\n🎭 CONVERSATION COMPLETE!")
    print(f"📊 Total messages: {total_message_count}")
    print(f"🔥 Provocations sent: {provocation_index}")
    print("🎯 Target pattern: Pinochet question to Kast, then alternating provocations")
    print("🤖 Neural Agent participated as question-asking moderator")
    print()
    
    # Interrupt timing analysis
    if interrupt_times:
        print("⏱️  INTERRUPT TIMING ANALYSIS:")
        print("-" * 50)
        print(f"📈 Total interrupts measured: {len(interrupt_times)}")
        print(f"🚀 Fastest interrupt: {min(interrupt_times):.3f} seconds")
        print(f"🐌 Slowest interrupt: {max(interrupt_times):.3f} seconds")
        print(f"📊 Average interrupt time: {sum(interrupt_times)/len(interrupt_times):.3f} seconds")
        print()
        print("📋 All interrupt times (seconds):")
        for i, duration in enumerate(interrupt_times, 1):
            print(f"   Interrupt #{i}: {duration:.3f}s")
        print()
        print(f"🔢 Interrupt raw array: {[round(t, 3) for t in interrupt_times]}")
    else:
        print("⚠️  No interrupts were measured during this test")
    
    print()
    
    # Send message timing analysis
    if send_message_times:
        print("📤 SEND MESSAGE TIMING ANALYSIS:")
        print("-" * 50)
        print(f"📈 Total sends measured: {len(send_message_times)}")
        print(f"🚀 Fastest send: {min(send_message_times):.3f} seconds")
        print(f"🐌 Slowest send: {max(send_message_times):.3f} seconds")
        print(f"📊 Average send time: {sum(send_message_times)/len(send_message_times):.3f} seconds")
        print()
        print("📋 All send message times (seconds):")
        for i, duration in enumerate(send_message_times, 1):
            print(f"   Send #{i}: {duration:.3f}s")
        print()
        print(f"🔢 Send message raw array: {[round(t, 3) for t in send_message_times]}")
    else:
        print("⚠️  No send messages were measured during this test")
    
    print("\n✅ 3-Agent interrupt functionality test completed!")

if __name__ == "__main__":
    asyncio.run(test_interrupt_with_real_agents())
