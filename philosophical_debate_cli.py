import asyncio
import curses
import sys
import os
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

class PhilosophicalDebateCLI:
    def __init__(self):
        self.running = True
        self.conversation_active = False
        self.awaiting_message = False
        self.display_lines: list[str] = []
        self.input_buffer: str = ""
        self.input_queue: asyncio.Queue[str] | None = None
        
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
    
    def _wrap_and_add(self, text: str, width: int) -> None:
        """Add text to display buffer, wrapping to terminal width, keep last 20 lines."""
        if width <= 0:
            width = 80
        for line in text.splitlines() or [""]:
            if len(line) == 0:
                self.display_lines.append("")
                continue
            start = 0
            while start < len(line):
                self.display_lines.append(line[start:start + width - 2])
                start += width - 2
        # Keep only last 20 lines
        if len(self.display_lines) > 20:
            self.display_lines = self.display_lines[-20:]

    def _render(self, stdscr) -> None:
        """Render header, message area (last 20 lines), and input box."""
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        header = "🧠 Debate: 'A Arte de Conhecer Si Mesmo'  —  Participantes: Kantiano | Nietzschiano | Existencialista | Budista"
        hint = "Comandos: 'i' = interromper; depois digite a mensagem."
        stdscr.addnstr(0, 0, header, width - 1)
        stdscr.addnstr(1, 0, hint, width - 1)
        stdscr.hline(2, 0, ord("-"), width - 1)

        # Message area occupies from row 3 to row height-3
        message_top = 3
        message_bottom = max(3, height - 3)
        visible_height = message_bottom - message_top
        # Show only last min(visible_height, 20) lines
        lines_to_show = self.display_lines[-min(visible_height, 20):]
        row = message_top
        for line in lines_to_show:
            if row >= message_bottom:
                break
            stdscr.addnstr(row, 0, line, width - 1)
            row += 1

        # Input box
        stdscr.hline(message_bottom, 0, ord("-"), width - 1)
        prompt = "Mensagem > " if self.awaiting_message else "Comando ('i' para interromper) > "
        input_line = f"{prompt}{self.input_buffer}"
        stdscr.addnstr(message_bottom + 1, 0, input_line, width - 1)
        # Move cursor to end of input
        cursor_x = min(len(input_line), width - 2)
        stdscr.move(message_bottom + 1, cursor_x)
        stdscr.refresh()

    async def _keyboard_loop(self, stdscr) -> None:
        """Collect keystrokes non-blockingly and push full lines to a queue."""
        assert self.input_queue is not None
        stdscr.nodelay(True)
        while self.running:
            try:
                ch = stdscr.getch()
            except Exception:
                ch = -1
            if ch == -1:
                await asyncio.sleep(0.05)
                continue
            # Handle keys
            if ch in (curses.KEY_ENTER, 10, 13):
                text = self.input_buffer.strip()
                self.input_buffer = ""
                await self.input_queue.put(text)
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                self.input_buffer = self.input_buffer[:-1]
            elif 0 <= ch < 256:
                self.input_buffer += chr(ch)
            self._render(stdscr)
    
    async def run_philosophical_debate_curses(self, stdscr):
        """Run the main philosophical debate with curses UI."""
        curses.curs_set(1)
        self.input_queue = asyncio.Queue()
        self.display_lines = []
        self.input_buffer = ""
        self.awaiting_message = False
        self.running = True

        # Setup
        agents = self.setup_agents()
        team, user_control = self.setup_team(agents)

        # Initial topic
        initial_topic = (
            "Vamos discutir 'A Arte de Conhecer Si Mesmo' de Arthur Schopenhauer.\n"
            "Começamos a discutir o livro."
        )

        # Render initial UI
        self._wrap_and_add("🚀 Iniciando debate filosófico...", stdscr.getmaxyx()[1])
        self._wrap_and_add("💡 Digite 'i' para interromper e, depois, escreva sua mensagem.", stdscr.getmaxyx()[1])
        self._render(stdscr)

        self.conversation_active = True

        # Start background keyboard loop
        kb_task = asyncio.create_task(self._keyboard_loop(stdscr))

        try:
            stream = team.run_stream(task=initial_topic)

            # We interleave stream consumption and user inputs (simple version)
            stream_iter = stream.__aiter__()
            next_msg_task = asyncio.create_task(stream_iter.__anext__())
            next_input_task = asyncio.create_task(self.input_queue.get())

            while self.running:
                done, _ = await asyncio.wait(
                    {next_msg_task, next_input_task}, return_when=asyncio.FIRST_COMPLETED
                )

                if next_msg_task in done:
                    try:
                        message = next_msg_task.result()
                    except StopAsyncIteration:
                        self._wrap_and_add("🏁 Debate encerrado.", stdscr.getmaxyx()[1])
                        self._render(stdscr)
                        break
                    if hasattr(message, "content") and hasattr(message, "source"):
                        ts = datetime.now().strftime("%H:%M:%S")
                        self._wrap_and_add(f"[{ts}] {message.source}: {message.content}", stdscr.getmaxyx()[1])
                    elif hasattr(message, "stop_reason"):
                        ts = datetime.now().strftime("%H:%M:%S")
                        self._wrap_and_add(f"[{ts}] Debate encerrado: {message.stop_reason}", stdscr.getmaxyx()[1])
                        self._render(stdscr)
                        break
                    self._render(stdscr)
                    next_msg_task = asyncio.create_task(stream_iter.__anext__())

                if next_input_task in done:
                    user_text = next_input_task.result()
                    next_input_task = asyncio.create_task(self.input_queue.get())
                    if not user_text:
                        continue
                    if not self.awaiting_message:
                        # Expecting an interrupt command first
                        if user_text.lower() == "i":
                            ts = datetime.now().strftime("%H:%M:%S")
                            self._wrap_and_add(f"[{ts}] 🛑 Interrompendo conversa...", stdscr.getmaxyx()[1])
                            await user_control.interrupt(team)
                            self.awaiting_message = True
                            self._wrap_and_add("💭 Escreva sua mensagem e pressione Enter.", stdscr.getmaxyx()[1])
                            self._render(stdscr)
                        else:
                            # Disregard messages before interrupt, as requested
                            self._wrap_and_add("ℹ️  Digite 'i' para interromper antes de enviar mensagem.", stdscr.getmaxyx()[1])
                            self._render(stdscr)
                    else:
                        # We are awaiting the user's message after interrupt
                        from random import choice
                        target = choice(["Kantiano", "Nietzschiano", "Existencialista", "Budista"])
                        ts = datetime.now().strftime("%H:%M:%S")
                        self._wrap_and_add(f"[{ts}] Moderador → {target}: {user_text}", stdscr.getmaxyx()[1])
                        self._render(stdscr)
                        result = await user_control.send(team, user_text, target)
                        # Display response
                        for msg in result.messages:
                            if hasattr(msg, "content") and hasattr(msg, "source") and msg.source != "RoundRobinGroupChatManager":
                                ts2 = datetime.now().strftime("%H:%M:%S")
                                self._wrap_and_add(f"[{ts2}] {msg.source}: {msg.content}", stdscr.getmaxyx()[1])
                        self.awaiting_message = False
                        self._render(stdscr)

        except KeyboardInterrupt:
            self._wrap_and_add("🛑 Debate interrompido pelo usuário.", stdscr.getmaxyx()[1])
            self._render(stdscr)
        finally:
            self.running = False
            self.conversation_active = False
            kb_task.cancel()
            try:
                await kb_task
            except Exception:
                pass

async def main_curses(stdscr):
    """Async entry point used within curses wrapper."""
    cli = PhilosophicalDebateCLI()
    await cli.run_philosophical_debate_curses(stdscr)

if __name__ == "__main__":
    try:
        curses.wrapper(lambda stdscr: asyncio.run(main_curses(stdscr)))
    except KeyboardInterrupt:
        print("\n\nSaindo...")
        sys.exit(0)
