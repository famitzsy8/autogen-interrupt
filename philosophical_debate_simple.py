import asyncio
import sys
import os
import threading
from datetime import datetime
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

class SimplePhilosophicalDebate:
    def __init__(self):
        self.running = True
        self.awaiting_message = False
        self.input_queue = asyncio.Queue()
        
    def setup_agents(self):
        """Create 4 philosophical agents for discussing Schopenhauer in Portuguese."""
        
        model_client = OpenAIChatCompletionClient(
            model="gpt-4o-mini",
            api_key=api_key,
        )
        
        # 1. Kantian Agent
        kantian = AssistantAgent(
            name="Kantiano",
            model_client=model_client,
            description="Filósofo seguidor de Immanuel Kant",
            system_message="""Você está discutindo "A Arte de Conhecer Si Mesmo" com 3 outros filósofos. Nunca diga TERMINATE."""
        )
        
        # 2. Nietzschean Agent  
        nietzschean = AssistantAgent(
            name="Nietzschiano",
            model_client=model_client,
            description="Filósofo seguidor de Friedrich Nietzsche",
            system_message="""Você está discutindo "A Arte de Conhecer Si Mesmo" com 3 outros filósofos. Nunca diga TERMINATE."""
        )
        
        # 3. Existentialist Agent
        existentialist = AssistantAgent(
            name="Existencialista",
            model_client=model_client,
            description="Filósofo existencialista",
            system_message="""Você está discutindo "A Arte de Conhecer Si Mesmo" com 3 outros filósofos. Nunca diga TERMINATE."""
        )
        
        # 4. Buddhist-influenced Agent
        buddhist = AssistantAgent(
            name="Budista",
            model_client=model_client,
            description="Filósofo com influências budistas",
            system_message="""Você está discutindo "A Arte de Conhecer Si Mesmo" com 3 outros filósofos. Nunca diga TERMINATE."""
        )
        
        return [kantian, nietzschean, existentialist, buddhist]
    
    def setup_team(self, agents):
        """Create the philosophical discussion team."""
        team = RoundRobinGroupChat(
            participants=agents,
            termination_condition=MaxMessageTermination(max_messages=50),
        )
        
        user_control = UserControlAgent(name="Moderador")
        return team, user_control
    
    def input_thread(self):
        """Thread function to handle user input non-blockingly."""
        while self.running:
            try:
                user_input = input()
                asyncio.run_coroutine_threadsafe(
                    self.input_queue.put(user_input), 
                    self.loop
                )
            except (EOFError, KeyboardInterrupt):
                break
    
    async def run_debate(self):
        """Run the philosophical debate with simple text interface."""
        print("🧠 Debate Filosófico: 'A Arte de Conhecer Si Mesmo' de Arthur Schopenhauer")
        print("=" * 70)
        print("Participantes: Kantiano | Nietzschiano | Existencialista | Budista")
        print("-" * 70)
        print("💡 COMANDOS:")
        print("   'i' + ENTER = Interromper a conversa")
        print("   Depois digite sua mensagem para um agente aleatório")
        print("=" * 70)
        
        # Setup
        agents = self.setup_agents()
        team, user_control = self.setup_team(agents)
        
        # Initial topic
        initial_topic = (
            "Vamos discutir 'A Arte de Conhecer Si Mesmo' de Arthur Schopenhauer. "
            "Começamos a discutir o livro."
        )
        
        # Start input thread
        self.loop = asyncio.get_event_loop()
        input_thread = threading.Thread(target=self.input_thread, daemon=True)
        input_thread.start()
        
        print("🚀 Iniciando debate...")
        print("💬 (Digite 'i' para interromper e depois sua mensagem)")
        print("-" * 70)
        
        try:
            stream = team.run_stream(task=initial_topic)
            
            # We interleave stream consumption and user inputs
            stream_iter = stream.__aiter__()
            next_msg_task = asyncio.create_task(stream_iter.__anext__())
            next_input_task = asyncio.create_task(self.input_queue.get())
            
            while self.running:
                done, _ = await asyncio.wait(
                    {next_msg_task, next_input_task}, 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                if next_msg_task in done:
                    try:
                        message = next_msg_task.result()
                    except StopAsyncIteration:
                        print("\n🏁 Debate encerrado.")
                        break
                    
                    if hasattr(message, "content") and hasattr(message, "source"):
                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"[{ts}] {message.source}: {message.content}")
                        print("-" * 40)
                    elif hasattr(message, "stop_reason"):
                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"[{ts}] Debate encerrado: {message.stop_reason}")
                        break
                    
                    next_msg_task = asyncio.create_task(stream_iter.__anext__())
                
                if next_input_task in done:
                    user_text = next_input_task.result()
                    next_input_task = asyncio.create_task(self.input_queue.get())
                    
                    if not user_text:
                        continue
                        
                    if not self.awaiting_message:
                        # Expecting an interrupt command first
                        if user_text.lower().strip() == "i":
                            ts = datetime.now().strftime("%H:%M:%S")
                            print(f"[{ts}] 🛑 INTERROMPENDO CONVERSA...")
                            await user_control.interrupt(team)
                            ts2 = datetime.now().strftime("%H:%M:%S")
                            print(f"[{ts2}] ✅ INTERRUPÇÃO CONCLUÍDA COM SUCESSO!")
                            print("💭 Agora digite sua mensagem e pressione ENTER:")
                            self.awaiting_message = True
                        else:
                            print("ℹ️  Digite 'i' para interromper antes de enviar mensagem.")
                    else:
                        # We are awaiting the user's message after interrupt
                        from random import choice
                        target = choice(["Kantiano", "Nietzschiano", "Existencialista", "Budista"])
                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"[{ts}] 💬 Moderador → {target}: {user_text}")
                        print("-" * 40)
                        
                        result = await user_control.send(team, user_text, target)
                        
                        # Display immediate responses
                        for msg in result.messages:
                            if hasattr(msg, "content") and hasattr(msg, "source") and msg.source != "RoundRobinGroupChatManager":
                                ts2 = datetime.now().strftime("%H:%M:%S")
                                print(f"[{ts2}] {msg.source}: {msg.content}")
                                print("-" * 40)
                        
                        self.awaiting_message = False
                        print("🔄 Continuando debate...")
                        
        except KeyboardInterrupt:
            print("\n🛑 Debate interrompido pelo usuário.")
        finally:
            self.running = False

async def main():
    """Main entry point."""
    debate = SimplePhilosophicalDebate()
    await debate.run_debate()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nSaindo...")
        sys.exit(0)
