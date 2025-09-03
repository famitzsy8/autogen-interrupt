"""
Stream accumulator that collects streaming tokens and creates complete messages
"""

import asyncio
import time
from helper.summarizer import LLMSummarizer

class StreamAccumulator:
    """Accumulates streaming tokens into complete messages"""
    
    def __init__(self, websocket_callback=None, allowed_agents=None):
        self.websocket_callback = websocket_callback
        self.summarizer = LLMSummarizer()
        self.current_agent = None
        self.message_buffer = ""
        self.last_token_time = 0
        self.finalize_task = None
        self.token_timeout = 0.5  # 0.5 seconds of silence triggers message finalization
        self.message_counter = 0
        self.allowed_agents = allowed_agents or ['orchestrator', 'committee_specialist']  # Default to 2-agent setup
        self.pending_tool_calls = {}  # Track pending tool calls
        self.investigation_terminated = False
        
    async def process_stream_message(self, message):
        """Process a single streaming message from AutoGen"""
        try:
            message_type = type(message).__name__
            source = getattr(message, 'source', 'unknown')
            content = getattr(message, 'content', '')
            
            # Only handle allowed agents
            if source not in self.allowed_agents:
                return
            
            if message_type == 'ModelClientStreamingChunkEvent':
                await self._handle_streaming_token(source, content)
            elif message_type in ['ToolCallRequestEvent', 'ToolCallExecutionEvent']:
                # For tool calls, finalize current message and handle separately
                await self._finalize_current_message()
                await self._handle_tool_event(source, message_type, content)
            else:
                # Other message types trigger finalization
                await self._finalize_current_message()
                print(f"🔄 Other message type: {message_type} from {source}")
                
        except Exception as e:
            print(f"Error processing stream message: {e}")
    
    async def _handle_streaming_token(self, agent_name: str, content: str):
        """Handle a streaming token from an agent"""
        # If this is from a different agent, finalize previous message
        if self.current_agent and self.current_agent != agent_name:
            await self._finalize_current_message()
        
        # Set/update current agent
        self.current_agent = agent_name
        
        # Add content to buffer
        if content and content.strip():
            self.message_buffer += content
            
            # Update last token time and reset timer
            self.last_token_time = time.time()
            await self._reset_finalize_timer()
    
    async def _handle_tool_event(self, agent_name: str, event_type: str, content):
        """Handle tool call events"""
        print(f"🔧 Tool event: {event_type} from {agent_name}")
        
        if event_type == 'ToolCallRequestEvent':
            await self._handle_tool_call_request(agent_name, content)
        elif event_type == 'ToolCallExecutionEvent':
            await self._handle_tool_call_result(agent_name, content)
    
    async def _handle_tool_call_request(self, agent_name: str, content):
        """Handle tool call request"""
        try:
            # Content should be a list of tool calls
            if isinstance(content, list):
                for tool_call in content:
                    tool_name = getattr(tool_call, 'name', 'unknown_tool')
                    arguments = getattr(tool_call, 'arguments', {})
                    call_id = getattr(tool_call, 'id', f'call_{int(time.time() * 1000)}')
                    
                    # Store pending tool call
                    self.pending_tool_calls[call_id] = {
                        'name': tool_name,
                        'arguments': arguments,
                        'agent': agent_name
                    }
                    
                    # Emit tool call start event
                    event = {
                        "type": "tool_call_start",
                        "timestamp": time.time(),
                        "data": {
                            "id": call_id,
                            "name": tool_name,
                            "arguments": arguments,
                            "agent": agent_name,
                            "status": "in_progress"
                        }
                    }
                    
                    if self.websocket_callback:
                        await self.websocket_callback(event)
                        print(f"📡 Sent tool call start: {tool_name} from {agent_name}")
            else:
                print(f"⚠️  Unexpected tool call content format: {type(content)}")
                
        except Exception as e:
            print(f"Error handling tool call request: {e}")
    
    async def _handle_tool_call_result(self, agent_name: str, content):
        """Handle tool call execution result"""
        try:
            # Content should be a list of tool call results
            if isinstance(content, list):
                for result in content:
                    tool_name = getattr(result, 'name', 'unknown_tool')
                    result_content = getattr(result, 'content', '')
                    call_id = getattr(result, 'call_id', f'result_{int(time.time() * 1000)}')
                    is_error = getattr(result, 'is_error', False)
                    
                    # Get original tool call info
                    tool_call_info = self.pending_tool_calls.get(call_id, {})
                    
                    # Generate LLM summaries
                    try:
                        summary = await self.summarizer.summarize_tool_call_result(tool_name, result_content)
                        details = await self.summarizer.parse_tool_call_details(
                            tool_name, 
                            tool_call_info.get('arguments', {}), 
                            result_content
                        )
                    except Exception as e:
                        print(f"LLM summarization failed for {tool_name}: {e}")
                        summary = f"Tool {tool_name} {'completed' if not is_error else 'failed'}"
                        details = {"raw_result": str(result_content)[:500]}
                    
                    # Emit tool call result event
                    event = {
                        "type": "tool_call_result",
                        "timestamp": time.time(),
                        "data": {
                            "id": call_id,
                            "name": tool_name,
                            "result": result_content,
                            "summary": summary,
                            "details": details,
                            "success": not is_error,
                            "agent": agent_name,
                            "status": "completed" if not is_error else "failed"
                        }
                    }
                    
                    if self.websocket_callback:
                        await self.websocket_callback(event)
                        print(f"📡 Sent tool call result: {tool_name} from {agent_name} - {summary}")
                    
                    # Remove from pending
                    if call_id in self.pending_tool_calls:
                        del self.pending_tool_calls[call_id]
            else:
                print(f"⚠️  Unexpected tool result content format: {type(content)}")
                
        except Exception as e:
            print(f"Error handling tool call result: {e}")
    
    async def _reset_finalize_timer(self):
        """Reset the timer that finalizes messages after silence"""
        # Cancel existing timer
        if self.finalize_task and not self.finalize_task.done():
            self.finalize_task.cancel()
        
        # Start new timer
        self.finalize_task = asyncio.create_task(self._delayed_finalize())
    
    async def _delayed_finalize(self):
        """Finalize message after timeout"""
        try:
            await asyncio.sleep(self.token_timeout)
            
            # Check if enough time has passed since last token
            if time.time() - self.last_token_time >= (self.token_timeout - 0.1):
                print(f"⏱️  Finalizing {self.current_agent} message after {self.token_timeout}s silence")
                await self._finalize_current_message()
        except asyncio.CancelledError:
            pass  # Timer was cancelled, that's normal
    
    async def _finalize_current_message(self):
        """Finalize and emit the current accumulated message"""
        if not self.current_agent or not self.message_buffer.strip():
            return
        
        content = self.message_buffer.strip()
        agent_name = self.current_agent
        
        print(f"✅ Finalizing message from {agent_name}: {len(content)} chars")
        print(f"📝 Preview: {content[:100]}...")
        
        try:
            # Check for TERMINATE before processing
            if self._check_for_terminate(content):
                await self._handle_investigation_termination(agent_name, content)
            
            # Generate summary
            summary = await self.summarizer.summarize_agent_communication(agent_name, content)
            
            # Create event
            self.message_counter += 1
            event = {
                "type": "agent_communication",
                "timestamp": time.time(),
                "data": {
                    "id": f"{agent_name}_{self.message_counter}_{int(time.time() * 1000)}",
                    "agent": agent_name,
                    "type": "message",
                    "simplified": summary,
                    "fullContent": content,
                    "toolCalls": [],
                    "results": [],
                    "status": "completed",
                    "contains_terminate": self._check_for_terminate(content)
                }
            }
            
            if self.websocket_callback:
                await self.websocket_callback(event)
                print(f"📡 Sent message to WebSocket: {summary}")
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            # Check for TERMINATE even if summary fails
            if self._check_for_terminate(content):
                await self._handle_investigation_termination(agent_name, content)
            
            # Send without summary if LLM fails
            if self.websocket_callback:
                event = {
                    "type": "agent_communication",
                    "timestamp": time.time(),
                    "data": {
                        "id": f"{agent_name}_{self.message_counter}_{int(time.time() * 1000)}",
                        "agent": agent_name,
                        "type": "message",
                        "simplified": content[:200] + "..." if len(content) > 200 else content,
                        "fullContent": content,
                        "toolCalls": [],
                        "results": [],
                        "status": "completed",
                        "contains_terminate": self._check_for_terminate(content)
                    }
                }
                await self.websocket_callback(event)
        
        # Reset state
        self.current_agent = None
        self.message_buffer = ""
        
        # Cancel timer
        if self.finalize_task and not self.finalize_task.done():
            self.finalize_task.cancel()
    
    def _detect_table_in_content(self, content: str) -> bool:
        """Detect if content contains a table structure"""
        content_lower = content.lower()
        
        # Look for table indicators
        table_indicators = [
            # Markdown table patterns
            '|', '---|', '---:', ':---',
            # Table keywords
            'table', 'summary', 'results',
            # Column-like patterns
            'name\t', 'company\t', 'date\t', 'amount\t',
            # Multiple rows of data patterns
            '\n1.', '\n2.', '\n3.',  # numbered lists
        ]
        
        # Check for pipe-separated values (markdown tables)
        lines = content.split('\n')
        table_like_lines = 0
        for line in lines:
            if '|' in line and line.count('|') >= 2:  # At least 3 columns
                table_like_lines += 1
        
        # If we have multiple pipe-separated lines, it's likely a table
        if table_like_lines >= 2:
            return True
        
        # Check for other table indicators
        for indicator in table_indicators:
            if indicator in content_lower:
                # Additional validation for keywords
                if indicator in ['table', 'summary', 'results']:
                    # Look for structured data nearby
                    if any(sep in content for sep in ['|', '\t', ':', '-']):
                        return True
        
        # Check for structured data patterns (multiple lines with similar format)
        structured_lines = 0
        for line in lines:
            if line.strip() and (':' in line or '-' in line or '|' in line):
                structured_lines += 1
        
        return structured_lines >= 3  # At least 3 structured lines
    
    def _parse_investigation_table(self, content: str) -> dict:
        """Parse investigation results table into structured data - supports dual tables"""
        import re
        
        lines = content.split('\n')
        parsed_data = {
            "aligned_members": [],
            "opposed_members": [],
            "members": [],  # Keep legacy support
            "summary": "",
            "table_type": "dual_table",
            "has_dual_tables": False
        }
        
        # Detect if we have dual tables (aligned vs opposed)
        dual_table_detected = self._detect_dual_tables(content)
        parsed_data["has_dual_tables"] = dual_table_detected
        
        if dual_table_detected:
            # Parse both tables by order: 1st = aligned, 2nd = opposed
            aligned_table = self._extract_table_by_order(content, 1)  # First table
            opposed_table = self._extract_table_by_order(content, 2)  # Second table
            
            if aligned_table:
                parsed_data["aligned_members"] = self._parse_single_table(aligned_table)
                print(f"✅ Parsed {len(parsed_data['aligned_members'])} aligned members")
            if opposed_table:
                parsed_data["opposed_members"] = self._parse_single_table(opposed_table)
                print(f"✅ Parsed {len(parsed_data['opposed_members'])} opposed members")
                
            # Combine for legacy compatibility
            parsed_data["members"] = parsed_data["aligned_members"] + parsed_data["opposed_members"]
            return parsed_data
        
        # Fall back to single table parsing
        # Look for different table patterns
        current_member = None
        in_table_section = False
        
        # Patterns to identify different data fields
        name_patterns = [
            r'^(?:(\d+)\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*(?:\s+[A-Z]+)?)\s*[\(\[]?([DR])[^\)]*[\)\]]?\s*[\(\[]?([A-Z]{2}(?:-\d+)?)[^\)]*[\)\]]?',  # Name with party and state
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)\s+\(([DR])-([A-Z]{2}(?:-\d+)?)\)',  # Name (Party-State)
            r'^(\d+)\.\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)',  # Numbered list
        ]
        
        # State/District patterns
        state_patterns = [
            r'\b([A-Z]{2})-(\d+)\b',  # State-District (e.g., TX-2)
            r'\b([A-Z]{2})\b(?!\-)',  # Just state (e.g., TX for Senate)
        ]
        
        # Party patterns
        party_patterns = [
            r'\b([DR])\b',  # D or R
            r'\b(Democrat|Republican)\b',  # Full party names
        ]
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Look for table headers or indicators
            if any(keyword in line.lower() for keyword in ['ranking', 'priority', 'members', 'representatives', 'senators', 'congress']):
                in_table_section = True
                parsed_data["table_type"] = "congressional_members"
                continue
            
            # Skip non-data lines
            if any(skip in line.lower() for skip in ['total', 'summary', 'note:', 'source:']):
                if 'summary' in line.lower():
                    parsed_data["summary"] = line
                continue
            
            if in_table_section and line:
                # Try to extract member information
                member_data = self._extract_member_data(line)
                if member_data:
                    parsed_data["members"].append(member_data)
        
        # If no structured parsing worked, try markdown table parsing
        if not parsed_data["members"]:
            fallback_parsed = self._parse_markdown_table(content)
            parsed_data.update(fallback_parsed)
        
        return parsed_data
    
    def _extract_member_data(self, line: str) -> dict:
        """Extract individual member data from a line"""
        import re
        
        # Clean the line
        line = line.strip()
        if not line or line.startswith('#'):
            return None
        
        member = {
            "name": "",
            "party": "",
            "state": "",
            "district": "",
            "ranking": "",
            "reason": "",
            "chamber": ""
        }
        
        # Pattern 1: Senator/Representative with full info
        # Example: "1. Senator Ted Cruz (R-TX) - Committee Chair on Energy and Natural Resources"
        pattern1 = r'^(\d+)\.?\s+(Senator|Representative)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)\s*\(([DR])-([A-Z]{2})(?:-(\d+))?\)\s*[-–]\s*(.+)$'
        match1 = re.match(pattern1, line)
        if match1:
            member["ranking"] = match1.group(1)
            chamber_title = match1.group(2)
            member["name"] = match1.group(3)
            member["party"] = "Democrat" if match1.group(4) == 'D' else "Republican"
            member["state"] = match1.group(5)
            member["district"] = match1.group(6) or ""
            member["chamber"] = "House" if chamber_title == "Representative" or match1.group(6) else "Senate"
            member["reason"] = match1.group(7)
            return member
        
        # Pattern 2: Name with title and location
        # Example: "2. Representative Alexandria Ocasio-Cortez (D-NY-14) - Vocal critic of fossil fuel lobbying"
        pattern2 = r'^(\d+)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)\s*\(([DR])-([A-Z]{2})(?:-(\d+))?\)\s*[-–]\s*(.+)$'
        match2 = re.match(pattern2, line)
        if match2:
            member["ranking"] = match2.group(1)
            member["name"] = match2.group(2)
            member["party"] = "Democrat" if match2.group(3) == 'D' else "Republican"
            member["state"] = match2.group(4)
            member["district"] = match2.group(5) or ""
            member["chamber"] = "House" if match2.group(5) else "Senate"
            member["reason"] = match2.group(6)
            return member
        
        # Pattern 3: Name with state in parentheses
        # Example: "Ted Cruz (R-Texas): Energy Committee Chair"
        pattern3 = r'^(?:(\d+)\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)\s*\(([DR])-([A-Za-z\s]+)\)\s*[:\-–]\s*(.+)$'
        match3 = re.match(pattern3, line)
        if match3:
            member["ranking"] = match3.group(1) or ""
            member["name"] = match3.group(2)
            member["party"] = "Democrat" if match3.group(3) == 'D' else "Republican"
            state_info = match3.group(4).strip()
            member["reason"] = match3.group(5)
            
            # Parse state info (could be "Texas", "NY-14", etc.)
            if '-' in state_info and len(state_info.split('-')[1].strip()) <= 3:
                parts = state_info.split('-')
                member["state"] = parts[0].strip()[:2].upper()  # Convert to state code
                member["district"] = parts[1].strip()
                member["chamber"] = "House"
            else:
                # Convert full state name to code if needed
                member["state"] = self._normalize_state_name(state_info)
                member["chamber"] = "Senate"
            
            return member
        
        # Pattern 4: Bullet point format
        # Example: "- Alexandria Ocasio-Cortez (NY-14, Democrat): Leading Green New Deal opponent"
        pattern4 = r'^[-•]\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)\s*\(([A-Z]{2}(?:-\d+)?),?\s*([A-Za-z]+)\)\s*[:\-–]\s*(.+)$'
        match4 = re.match(pattern4, line)
        if match4:
            member["name"] = match4.group(1)
            location = match4.group(2)
            party = match4.group(3)
            member["reason"] = match4.group(4)
            
            if '-' in location:
                parts = location.split('-')
                member["state"] = parts[0]
                member["district"] = parts[1]
                member["chamber"] = "House"
            else:
                member["state"] = location
                member["chamber"] = "Senate"
            
            member["party"] = "Democrat" if party.lower().startswith('d') else "Republican" if party.lower().startswith('r') else party
            return member
        
        # Pattern 5: Markdown table row
        # Example: "| Ted Cruz | TX | R | Energy Committee Chair | High - Industry connections |"
        if line.startswith('|') and line.endswith('|') and line.count('|') >= 4:
            parts = [part.strip() for part in line.split('|')[1:-1]]  # Remove empty first/last
            if len(parts) >= 4:
                member["name"] = parts[0]
                member["state"] = parts[1]
                party_raw = parts[2]
                member["party"] = "Democrat" if party_raw == 'D' else "Republican" if party_raw == 'R' else party_raw
                
                # Combine committee role and influence level as reason
                committee_role = parts[3] if len(parts) > 3 else ""
                influence = parts[4] if len(parts) > 4 else ""
                member["reason"] = f"{committee_role} - {influence}".strip(" -")
                
                # Determine chamber based on district info in state
                if '-' in member["state"]:
                    state_parts = member["state"].split('-')
                    member["state"] = state_parts[0]
                    member["district"] = state_parts[1]
                    member["chamber"] = "House"
                else:
                    member["chamber"] = "Senate"
                
                return member
        
        # Pattern 6: Simple narrative mentions
        # Example: "Ted Cruz from Texas (Republican, Energy Committee)"
        pattern6 = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)\s+from\s+([A-Za-z\s]+)(?:\'s\s+(\d+)(?:nd|rd|th|st)?\s+district)?\s*\(([^)]+)\)'
        match6 = re.search(pattern6, line)
        if match6:
            member["name"] = match6.group(1)
            state_info = match6.group(2).strip()
            district = match6.group(3)
            description = match6.group(4)
            
            member["state"] = self._normalize_state_name(state_info)
            member["district"] = district or ""
            member["chamber"] = "House" if district else "Senate"
            member["reason"] = description
            
            # Extract party from description if possible
            if "Republican" in description or "GOP" in description:
                member["party"] = "Republican"
            elif "Democrat" in description or "Democratic" in description:
                member["party"] = "Democrat"
            
            return member
        
        return None
    
    def _detect_dual_tables(self, content: str) -> bool:
        """"Detect if content contains exactly two separate tables"""
        # Count actual table headers (not just separators)
        lines = content.split('\n')
        table_header_count = 0
        
        for line in lines:
            line_lower = line.lower().strip()
            # Look for markdown table headers with the expected columns
            if ('|' in line and 
                'congress member' in line_lower and 
                ('chamber' in line_lower or 'party' in line_lower) and
                'involvement rank' in line_lower):
                table_header_count += 1
        
        print(f"🔍 Dual table detection: found {table_header_count} table headers")
        
        # Simple requirement: exactly 2 table headers
        return table_header_count == 2
    
    def _extract_table_by_order(self, content: str, table_number: int) -> str:
        """Extract first or second table based on order (1=first, 2=second)"""
        lines = content.split('\n')
        tables_found = []
        current_table_lines = []
        in_table = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Look for table headers
            if ('|' in line and 
                'congress member' in line_lower and 
                ('chamber' in line_lower or 'party' in line_lower) and
                'involvement rank' in line_lower):
                
                # If we were already in a table, save the previous one
                if in_table and current_table_lines:
                    tables_found.append('\n'.join(current_table_lines))
                    current_table_lines = []
                
                # Start new table
                in_table = True
                current_table_lines.append(line)
                print(f"📊 Found table #{len(tables_found) + 1} header at line {i}: {line.strip()}")
                continue
            
            # Collect table content if we're in a table
            if in_table:
                # Include separator lines and data rows
                if '|' in line:
                    # Check if this is a separator line
                    if line.strip().replace('|', '').replace('-', '').replace(':', '').strip() == '':
                        current_table_lines.append(line)  # Separator line
                        continue
                    
                    # Check if this is a data row (has enough columns)
                    if line.count('|') >= 4:  # At least 5 columns expected
                        current_table_lines.append(line)
                        continue
                
                # Stop conditions for current table
                # 1. Empty line after table content
                if line.strip() == '' and len(current_table_lines) > 2:
                    tables_found.append('\n'.join(current_table_lines))
                    current_table_lines = []
                    in_table = False
                    continue
                    
                # 2. Non-table line after table started
                if not ('|' in line) and len(current_table_lines) > 2:
                    print(f"🛑 Table #{len(tables_found) + 1} ended at line {i}: {line.strip()}")
                    tables_found.append('\n'.join(current_table_lines))
                    current_table_lines = []
                    in_table = False
        
        # Don't forget the last table if we ended while in one
        if in_table and current_table_lines:
            tables_found.append('\n'.join(current_table_lines))
        
        print(f"📋 Found {len(tables_found)} total tables")
        
        # Return the requested table (1-indexed)
        if table_number <= len(tables_found):
            result = tables_found[table_number - 1]
            line_count = len(result.split("\n"))
            print(f"✅ Returning table #{table_number} with {line_count} lines")
            return result
        else:
            print(f"❌ Table #{table_number} not found, only have {len(tables_found)} tables")
            return ""
    
    def _parse_single_table(self, table_content: str) -> list:
        """Parse a single table and return list of members with improved accuracy"""
        if not table_content.strip():
            return []
        
        print(f"🔧 Parsing table content:\n{table_content}")
        
        lines = table_content.split('\n')
        members = []
        header_found = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Skip header line
            if not header_found and 'congress member' in line.lower():
                header_found = True
                print(f"📋 Found header at line {i}: {line}")
                continue
            
            # Skip separator line  
            if line.replace('|', '').replace('-', '').replace(':', '').strip() == '':
                continue
            
            # Parse data rows
            if '|' in line and header_found:
                member = self._parse_table_row_improved(line)
                if member:
                    members.append(member)
                    print(f"✅ Parsed member: {member.get('name', 'Unknown')} - Rank {member.get('ranking', 'N/A')}")
                else:
                    print(f"❌ Failed to parse line: {line}")
        
        print(f"📊 Total members parsed: {len(members)}")
        return members
    
    def _parse_table_row_improved(self, row: str) -> dict:
        """Parse a single table row with improved accuracy"""
        try:
            # Split by | and clean up
            cells = [cell.strip() for cell in row.split('|') if cell.strip()]
            
            if len(cells) < 5:
                print(f"⚠️  Row has insufficient columns ({len(cells)}): {row}")
                return None
            
            # Expected format: | Name (Party) | Chamber | State/District | Rank | Reason |
            name_cell = cells[0] if len(cells) > 0 else ""
            chamber_cell = cells[1] if len(cells) > 1 else ""
            state_district_cell = cells[2] if len(cells) > 2 else ""
            rank_cell = cells[3] if len(cells) > 3 else ""
            reason_cell = cells[4] if len(cells) > 4 else ""
            
            # Parse name and extract party if present
            name, party = self._parse_name_and_party(name_cell)
            
            # Parse rank
            rank = self._extract_rank(rank_cell)
            
            # Parse state/district
            state, district = self._parse_state_district(state_district_cell)
            
            # Determine chamber
            chamber = "House" if district else "Senate"
            if chamber_cell.lower().startswith('rep'):
                chamber = "House"
            elif chamber_cell.lower().startswith('sen'):
                chamber = "Senate"
            
            member = {
                "name": name,
                "party": party,
                "state": state,
                "district": district,
                "ranking": str(rank) if rank else "",
                "reason": reason_cell,
                "chamber": chamber
            }
            
            return member
            
        except Exception as e:
            print(f"Error parsing table row: {e}")
            return None
    
    def _parse_name_and_party(self, name_cell: str) -> tuple:
        """Extract name and party from name cell"""
        import re
        
        # Pattern: "John Doe (R)" or "Jane Smith (D)"
        party_match = re.search(r'\(([RDI])\)', name_cell)
        if party_match:
            party = party_match.group(1)
            name = re.sub(r'\s*\([RDI]\)', '', name_cell).strip()
            return name, party
        
        return name_cell.strip(), ""
    
    def _extract_rank(self, rank_cell: str) -> int:
        """Extract numeric rank from rank cell"""
        import re
        match = re.search(r'(\d+)', rank_cell)
        if match:
            return int(match.group(1))
        return None
    
    def _parse_state_district(self, state_district_cell: str) -> tuple:
        """Parse state and district from state/district cell"""
        # Pattern: "MD-03" -> ("MD", "03") or "TN" -> ("TN", None)
        if '-' in state_district_cell and len(state_district_cell.split('-')) == 2:
            parts = state_district_cell.split('-')
            return parts[0].strip(), parts[1].strip()
        
        return state_district_cell.strip(), None
    
    def _normalize_state_name(self, state_name: str) -> str:
        """Convert full state names to standard 2-letter codes"""
        state_mapping = {
            'texas': 'TX', 'california': 'CA', 'new york': 'NY', 'florida': 'FL',
            'alaska': 'AK', 'west virginia': 'WV', 'massachusetts': 'MA',
            'wyoming': 'WY', 'rhode island': 'RI', 'montana': 'MT'
        }
        
        normalized = state_name.lower().strip()
        return state_mapping.get(normalized, state_name.upper()[:2])
    
    def _parse_markdown_table(self, content: str) -> dict:
        """Parse markdown-style table from content"""
        lines = content.split('\n')
        parsed_data = {
            "members": [],
            "summary": "",
            "table_type": "markdown_table"
        }
        
        in_table = False
        headers = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Look for table headers first
            if '|' in line and not in_table:
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                if len(cells) >= 3 and any(keyword in ' '.join(cells).lower() for keyword in ['member', 'name', 'state', 'party', 'committee']):
                    headers = cells
                    continue
            
            # Check for table separator line (e.g., |---|---|---|)
            if '|' in line and ('-' in line or '=' in line):
                in_table = True
                continue
            
            # Process table rows
            if '|' in line and (in_table or len(headers) > 0):
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                
                # Skip header row if we haven't marked in_table yet
                if not in_table and headers:
                    in_table = True
                    if cells == headers:  # This is the header row repeated
                        continue
                
                # Process data row
                if len(cells) >= 3:  # Need at least name, state, something
                    member = {
                        "name": "",
                        "party": "",
                        "state": "",
                        "district": "",
                        "ranking": "",
                        "reason": "",
                        "chamber": ""
                    }
                    
                    # Standard table format: Name | State | Party | Role | Influence
                    if len(cells) >= 4:
                        member["name"] = cells[0]
                        
                        # Parse state (could include district)
                        state_cell = cells[1]
                        if '-' in state_cell and len(state_cell.split('-')[1]) <= 3:
                            parts = state_cell.split('-')
                            member["state"] = parts[0]
                            member["district"] = parts[1]
                            member["chamber"] = "House"
                        else:
                            member["state"] = state_cell
                            member["chamber"] = "Senate"
                        
                        # Parse party
                        party_cell = cells[2]
                        if party_cell in ['D', 'R']:
                            member["party"] = "Democrat" if party_cell == 'D' else "Republican"
                        else:
                            member["party"] = party_cell
                        
                        # Combine remaining cells as reason
                        reason_parts = cells[3:]
                        member["reason"] = " - ".join(reason_parts).strip(" -")
                        
                        if member["name"] and member["name"] not in ['Member Name', 'Name']:
                            parsed_data["members"].append(member)
                    
                    # Alternative format: Name | Location | Description
                    elif len(cells) == 3:
                        member["name"] = cells[0]
                        location = cells[1]
                        member["reason"] = cells[2]
                        
                        # Parse location
                        if '-' in location and len(location.split('-')[1]) <= 3:
                            parts = location.split('-')
                            member["state"] = parts[0]
                            member["district"] = parts[1]
                            member["chamber"] = "House"
                        else:
                            member["state"] = location
                            member["chamber"] = "Senate"
                        
                        if member["name"] and member["name"] not in ['Member Name', 'Name']:
                            parsed_data["members"].append(member)
        
        return parsed_data
    
    def _check_for_terminate(self, content: str) -> bool:
        """Check if content contains TERMINATE keyword"""
        return 'TERMINATE' in content.upper()
    
    async def _handle_investigation_termination(self, agent_name: str, content: str):
        """Handle investigation termination and table detection"""
        if self.investigation_terminated:
            return  # Already handled
        
        self.investigation_terminated = True
        
        # Check for table in the termination message
        has_table = self._detect_table_in_content(content)
        parsed_table_data = None
        
        if has_table:
            # Parse the table data
            parsed_table_data = self._parse_investigation_table(content)
            print(f"📊 Parsed table data: {len(parsed_table_data.get('members', []))} members found")
        
        # Create termination event
        termination_event = {
            "type": "investigation_concluded",
            "timestamp": time.time(),
            "data": {
                "id": f"conclusion_{int(time.time() * 1000)}",
                "agent": agent_name,
                "status": "concluded",
                "table_available": has_table,
                "conclusion_message": "Investigation concluded successfully",
                "table_status": "Table available in final results" if has_table else "No table found in final results",
                "table_data": parsed_table_data
            }
        }
        
        if self.websocket_callback:
            await self.websocket_callback(termination_event)
            print(f"🏁 Investigation concluded by {agent_name}, table {'available' if has_table else 'unavailable'}")
    
    async def finish(self):
        """Finalize any remaining message when stream ends"""
        await self._finalize_current_message()