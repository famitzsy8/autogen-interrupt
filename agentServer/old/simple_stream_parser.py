"""
Simple stream parser based on actual AutoGen Console output patterns observed in logging_test.py
"""

import asyncio
import time
from llm_summarizer import LLMSummarizer

class SimpleStreamParser:
    """Parse AutoGen Console stream output directly, based on observed patterns"""
    
    def __init__(self, websocket_callback=None):
        self.websocket_callback = websocket_callback
        self.summarizer = LLMSummarizer()
        self.current_agent = None
        self.message_buffer = ""
        self.in_agent_response = False
        self.last_token_time = 0
        self.finalize_task = None
        self.token_timeout = 1.5  # 1.5 seconds without new tokens triggers finalization
        self.message_id_counter = 0
        
    async def process_console_line(self, line: str):
        """Process a single line from AutoGen Console output"""
        stripped = line.strip()
        
        # Check for agent response start pattern
        if stripped.startswith("---------- ModelClientStreamingChunkEvent (") and stripped.endswith(") ----------"):
            await self._handle_agent_start(stripped)
        elif stripped.startswith("---------- TextMessage (") and stripped.endswith(") ----------"):
            await self._handle_user_message_start()
        elif stripped.startswith("---------- ToolCallRequestEvent (") and stripped.endswith(") ----------"):
            await self._handle_tool_call_start(stripped)
        elif stripped.startswith("---------- ToolCallExecutionEvent (") and stripped.endswith(") ----------"):
            await self._handle_tool_result_start(stripped)
        elif stripped.startswith("----------") and stripped.endswith("----------"):
            # Other delimiters - only finalize if it's a significant context change
            if "TextMessage" in stripped or "TeamMessage" in stripped or "GroupChatMessage" in stripped:
                await self._finalize_current_message()
                self.in_agent_response = False
                print(f"🔄 Context change detected: {stripped}")
        else:
            # Regular content line
            if self.in_agent_response:
                self.message_buffer += line + "\n"
                # Reset the finalization timer
                await self._reset_finalize_timer()
    
    async def _handle_agent_start(self, delimiter: str):
        """Handle start of agent response"""
        # Extract agent name
        import re
        match = re.search(r'ModelClientStreamingChunkEvent \(([^)]+)\)', delimiter)
        if match:
            agent_name = match.group(1)
            
            # Only process our 2 agents
            if agent_name in ['orchestrator', 'committee_specialist']:
                # If it's the same agent, just continue buffering (streaming tokens)
                if self.current_agent == agent_name and self.in_agent_response:
                    return  # Continue building the same message
                
                # If it's a different agent or first message, finalize previous and start new
                await self._finalize_current_message()
                
                self.current_agent = agent_name
                self.message_buffer = ""
                self.in_agent_response = True
                print(f"🎯 Starting to capture {agent_name} response...")
            else:
                print(f"⏭️  Ignoring response from {agent_name} (not in 2-agent setup)")
                # Don't change state if we're capturing a different agent
                if agent_name != self.current_agent:
                    self.in_agent_response = False
    
    async def _handle_user_message_start(self):
        """Handle start of user message"""
        await self._finalize_current_message()
        self.in_agent_response = False
        print("👤 User message detected")
    
    async def _handle_tool_call_start(self, delimiter: str):
        """Handle tool call request"""
        await self._finalize_current_message()
        
        import re
        match = re.search(r'ToolCallRequestEvent \(([^)]+)\)', delimiter)
        if match:
            agent_name = match.group(1)
            if agent_name in ['orchestrator', 'committee_specialist']:
                print(f"🔧 Tool call from {agent_name}...")
                # We'll capture the tool call details in the next lines
                self.current_agent = agent_name
                self.in_agent_response = True
                self.message_buffer = ""
    
    async def _handle_tool_result_start(self, delimiter: str):
        """Handle tool call result"""
        await self._finalize_current_message()
        
        import re
        match = re.search(r'ToolCallExecutionEvent \(([^)]+)\)', delimiter)
        if match:
            agent_name = match.group(1)
            if agent_name in ['orchestrator', 'committee_specialist']:
                print(f"📊 Tool result from {agent_name}...")
                self.current_agent = agent_name
                self.in_agent_response = True
                self.message_buffer = ""
    
    async def _finalize_current_message(self):
        """Finalize and emit the current message"""
        if not self.in_agent_response or not self.current_agent or not self.message_buffer.strip():
            return
        
        content = self.message_buffer.strip()
        agent_name = self.current_agent
        
        print(f"✅ Finalizing message from {agent_name} ({len(content)} chars)")
        
        # Generate summary
        summary = await self.summarizer.summarize_agent_communication(agent_name, content)
        
        # Create event
        event = {
            "type": "agent_communication",
            "timestamp": time.time(),
            "data": {
                "id": f"{agent_name}_{int(time.time() * 1000)}",
                "agent": agent_name,
                "type": "message",
                "simplified": summary,
                "fullContent": content,
                "toolCalls": [],
                "results": [],
                "status": "completed"
            }
        }
        
        if self.websocket_callback:
            await self.websocket_callback(event)
        
        # Reset
        self.current_agent = None
        self.message_buffer = ""
        self.in_agent_response = False
        self._cancel_finalize_timer()
    
    async def _reset_finalize_timer(self):
        """Reset the timer that finalizes messages after inactivity"""
        self.last_token_time = time.time()
        
        # Cancel existing timer
        self._cancel_finalize_timer()
        
        # Start new timer
        self.finalize_task = asyncio.create_task(self._delayed_finalize())
    
    def _cancel_finalize_timer(self):
        """Cancel the finalization timer"""
        if self.finalize_task and not self.finalize_task.done():
            self.finalize_task.cancel()
            self.finalize_task = None
    
    async def _delayed_finalize(self):
        """Finalize message after timeout"""
        try:
            await asyncio.sleep(self.token_timeout)
            
            # Check if enough time has passed since last token
            if time.time() - self.last_token_time >= self.token_timeout:
                print(f"⏱️  Timeout reached, finalizing {self.current_agent} message")
                await self._finalize_current_message()
        except asyncio.CancelledError:
            pass  # Timer was cancelled, that's normal