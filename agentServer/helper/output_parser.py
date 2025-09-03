"""
Intelligent parser for AutoGen console outputs that waits for complete agent responses
and creates structured communication events.
"""

import re
import json
import asyncio
from typing import Dict, List, Optional, Callable
from enum import Enum
from helper.llm_summarizer import LLMSummarizer

class ParseState(Enum):
    WAITING = "waiting"
    PARSING_AGENT_COMMUNICATION = "parsing_communication"
    PARSING_TOOL_CALL = "parsing_tool_call"
    PARSING_TOOL_RESULT = "parsing_tool_result"

class AutoGenOutputParser:
    def __init__(self, event_callback: Optional[Callable] = None):
        self.event_callback = event_callback
        self.summarizer = LLMSummarizer()
        self.state = ParseState.WAITING
        self.current_buffer = ""
        self.current_agent = ""
        self.current_tool_calls = []
        self.pending_tool_calls = {}  # track tool calls waiting for results
        
    def process_line(self, line: str):
        """Process a single line of AutoGen output"""
        asyncio.create_task(self._process_line_async(line))
    
    async def _process_line_async(self, line: str):
        """Async processing of output lines"""
        stripped_line = line.strip()
        
        # Check for section delimiters
        if stripped_line.startswith("----------") and stripped_line.endswith("----------"):
            await self._handle_section_delimiter(stripped_line)
        else:
            # Add to current buffer
            self.current_buffer += line + "\n"
            
            # Check for specific patterns within sections
            if self.state == ParseState.PARSING_TOOL_CALL:
                await self._parse_tool_call_content()
            elif self.state == ParseState.PARSING_TOOL_RESULT:
                await self._parse_tool_result_content()
    
    async def _handle_section_delimiter(self, delimiter: str):
        """Handle section delimiters and emit events for completed sections"""
        
        # First, emit any pending communication
        if self.state == ParseState.PARSING_AGENT_COMMUNICATION and self.current_buffer.strip():
            await self._emit_agent_communication()
        
        # Parse the new delimiter
        if "ModelClientStreamingChunkEvent" in delimiter:
            # Start of agent communication
            agent_match = re.search(r'ModelClientStreamingChunkEvent \(([^)]+)\)', delimiter)
            if agent_match:
                self.current_agent = agent_match.group(1)
                self.state = ParseState.PARSING_AGENT_COMMUNICATION
                self.current_buffer = ""
        
        elif "ToolCallRequestEvent" in delimiter:
            # Start of tool call
            agent_match = re.search(r'ToolCallRequestEvent \(([^)]+)\)', delimiter)
            if agent_match:
                self.current_agent = agent_match.group(1)
                self.state = ParseState.PARSING_TOOL_CALL
                self.current_buffer = ""
        
        elif "ToolCallExecutionEvent" in delimiter:
            # Start of tool call result
            agent_match = re.search(r'ToolCallExecutionEvent \(([^)]+)\)', delimiter)
            if agent_match:
                self.current_agent = agent_match.group(1)
                self.state = ParseState.PARSING_TOOL_RESULT
                self.current_buffer = ""
        
        else:
            # Other delimiter, reset state
            self.state = ParseState.WAITING
            self.current_buffer = ""
    
    async def _emit_agent_communication(self):
        """Emit a complete agent communication event"""
        if not self.current_buffer.strip() or not self.current_agent:
            return
        
        # Clean up the content
        content = self._clean_content(self.current_buffer)
        
        # Generate summary using LLM
        summary = await self.summarizer.summarize_agent_communication(
            self.current_agent, 
            content
        )
        
        # Create communication event
        event = {
            "type": "agent_communication",
            "timestamp": asyncio.get_event_loop().time(),
            "data": {
                "id": f"{self.current_agent}_{int(asyncio.get_event_loop().time() * 1000)}",
                "agent": self.current_agent,
                "type": "message",
                "simplified": summary,
                "fullContent": content,
                "toolCalls": [],
                "results": [],
                "status": "completed"
            }
        }
        
        if self.event_callback:
            await self.event_callback(event)
    
    async def _parse_tool_call_content(self):
        """Parse tool call content from buffer"""
        # Look for FunctionCall pattern
        function_call_pattern = r'\[FunctionCall\([^]]+\)\]'
        matches = re.findall(function_call_pattern, self.current_buffer)
        
        if matches:
            for match in matches:
                await self._parse_function_call(match)
    
    async def _parse_function_call(self, function_call_str: str):
        """Parse a single FunctionCall string"""
        try:
            # Extract id, name, and arguments from FunctionCall string
            id_match = re.search(r"id='([^']+)'", function_call_str)
            name_match = re.search(r"name='([^']+)'", function_call_str)
            args_match = re.search(r"arguments='([^']+)'", function_call_str)
            
            if id_match and name_match:
                call_id = id_match.group(1)
                tool_name = name_match.group(1)
                arguments_str = args_match.group(1) if args_match else "{}"
                
                try:
                    arguments = json.loads(arguments_str)
                except:
                    arguments = {}
                
                # Store pending tool call
                self.pending_tool_calls[call_id] = {
                    "name": tool_name,
                    "arguments": arguments,
                    "agent": self.current_agent
                }
                
                # Emit tool call start event
                event = {
                    "type": "tool_call_start",
                    "timestamp": asyncio.get_event_loop().time(),
                    "data": {
                        "id": call_id,
                        "name": tool_name,
                        "arguments": arguments,
                        "agent": self.current_agent,
                        "status": "in_progress"
                    }
                }
                
                if self.event_callback:
                    await self.event_callback(event)
        
        except Exception as e:
            print(f"Error parsing function call: {e}")
    
    async def _parse_tool_result_content(self):
        """Parse tool call result content from buffer"""
        # Look for FunctionExecutionResult pattern
        result_pattern = r'FunctionExecutionResult\([^)]+\)'
        matches = re.findall(result_pattern, self.current_buffer)
        
        if matches:
            for match in matches:
                await self._parse_function_result(match)
    
    async def _parse_function_result(self, result_str: str):
        """Parse a single FunctionExecutionResult string"""
        try:
            # Extract call_id, content, name, is_error
            call_id_match = re.search(r"call_id='([^']+)'", result_str)
            name_match = re.search(r"name='([^']+)'", result_str)
            content_match = re.search(r"content='([^']+)'", result_str)
            error_match = re.search(r"is_error=([^,)]+)", result_str)
            
            if call_id_match and name_match:
                call_id = call_id_match.group(1)
                tool_name = name_match.group(1)
                content = content_match.group(1) if content_match else ""
                is_error = error_match.group(1).strip() == "True" if error_match else False
                
                # Get original tool call info
                tool_call_info = self.pending_tool_calls.get(call_id, {})
                agent_name = tool_call_info.get("agent", self.current_agent)
                
                # Generate summary using LLM
                summary = await self.summarizer.summarize_tool_call_result(tool_name, content)
                
                # Parse detailed results
                details = await self.summarizer.parse_tool_call_details(
                    tool_name, 
                    tool_call_info.get("arguments", {}), 
                    content
                )
                
                # Emit tool call result event
                event = {
                    "type": "tool_call_result",
                    "timestamp": asyncio.get_event_loop().time(),
                    "data": {
                        "id": call_id,
                        "name": tool_name,
                        "result": content,
                        "summary": summary,
                        "details": details,
                        "success": not is_error,
                        "agent": agent_name,
                        "status": "completed" if not is_error else "failed"
                    }
                }
                
                if self.event_callback:
                    await self.event_callback(event)
                
                # Remove from pending
                if call_id in self.pending_tool_calls:
                    del self.pending_tool_calls[call_id]
        
        except Exception as e:
            print(f"Error parsing function result: {e}")
    
    def _clean_content(self, content: str) -> str:
        """Clean up content by removing log lines and extra whitespace"""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip log lines
            if any(log_pattern in line for log_pattern in [
                "INFO     Processing request",
                "INFO     HTTP Request:",
                "INFO     Warning:",
                "INFO     Anonymized telemetry"
            ]):
                continue
            
            # Skip empty lines
            if not line.strip():
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()

class ParseToolCallResultDetails:
    """Utility for parsing and formatting tool call results for detailed display"""
    
    @staticmethod
    def format_for_ui(tool_name: str, result_data: dict) -> dict:
        """Format tool call results for UI display"""
        
        if tool_name == "getBillSponsors":
            return ParseToolCallResultDetails._format_bill_sponsors(result_data)
        elif tool_name == "getBillCommittees":
            return ParseToolCallResultDetails._format_bill_committees(result_data)
        elif tool_name == "getRelevantBillSections":
            return ParseToolCallResultDetails._format_bill_sections(result_data)
        else:
            return ParseToolCallResultDetails._format_generic(tool_name, result_data)
    
    @staticmethod
    def _format_bill_sponsors(data: dict) -> dict:
        """Format bill sponsors data"""
        try:
            sponsors = data.get("sponsors", [])
            return {
                "title": f"Found {len(sponsors)} Bill Sponsor(s)",
                "items": [
                    f"{sponsor.get('full_name', 'Unknown')} ({sponsor.get('party', '?')}-{sponsor.get('state', '??')})"
                    for sponsor in sponsors
                ],
                "count": len(sponsors)
            }
        except:
            return {"title": "Bill Sponsors Retrieved", "items": ["Data available"], "count": 1}
    
    @staticmethod
    def _format_bill_committees(data: dict) -> dict:
        """Format bill committees data"""
        try:
            committees = data.get("committees", [])
            items = []
            for committee in committees:
                name = committee.get("name", "Unknown Committee")
                subcommittees = committee.get("subcommittees", [])
                if subcommittees:
                    items.append(f"{name} ({len(subcommittees)} subcommittees)")
                else:
                    items.append(name)
            
            return {
                "title": f"Found {len(committees)} Committee(s)",
                "items": items,
                "count": len(committees)
            }
        except:
            return {"title": "Bill Committees Retrieved", "items": ["Data available"], "count": 1}
    
    @staticmethod
    def _format_bill_sections(data: str) -> dict:
        """Format bill sections data"""
        try:
            sections = data.split("SEC. ")
            section_count = len([s for s in sections if s.strip()]) - 1  # -1 for empty first split
            return {
                "title": f"Retrieved {section_count} Relevant Section(s)",
                "items": [f"Section {i+1}: {s.split('.')[0] if '.' in s else 'Content'}" 
                         for i, s in enumerate(sections[1:6])],  # Show first 5
                "count": section_count
            }
        except:
            return {"title": "Bill Sections Retrieved", "items": ["Relevant content found"], "count": 1}
    
    @staticmethod
    def _format_generic(tool_name: str, data) -> dict:
        """Generic formatter for unknown tool types"""
        return {
            "title": f"{tool_name} Completed",
            "items": ["Results retrieved successfully"],
            "count": 1
        }