"""
Investigation Logger - Captures and analyzes AutoGen investigation logs
"""

import logging
import json
import re
import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class LogEvent:
    timestamp: str
    level: str
    source: str
    event_type: str
    content: str
    session_id: Optional[str] = None
    agent_name: Optional[str] = None
    error_info: Optional[str] = None
    raw_message: Optional[str] = None

class InvestigationLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup main log file
        self.setup_logging()
        
        # Event storage
        self.events: List[LogEvent] = []
        self.current_session: Optional[str] = None
        
        # Patterns for parsing
        self.patterns = {
            'session_id': re.compile(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'),
            'agent_name': re.compile(r'(orchestrator|committee_specialist|bill_specialist|actions_specialist|amendment_specialist|congress_member_specialist)'),
            'openai_error': re.compile(r'(429|Too Many Requests|rate limit|Retrying request)', re.IGNORECASE),
            'tool_call': re.compile(r'tool_call|ToolCallEvent'),
            'completion': re.compile(r'investigation_complete|investigation_concluded'),
            'error': re.compile(r'ERROR|Exception|Traceback', re.IGNORECASE)
        }
    
    def setup_logging(self):
        """Setup structured logging to file"""
        # Create session-specific log file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"investigation_{timestamp}.log"
        
        # Configure logger
        self.logger = logging.getLogger('investigation')
        self.logger.setLevel(logging.INFO)
        
        # File handler with detailed format
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # NO console handler - file only to avoid console overflow
        
        # Formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        )
        
        file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(file_handler)
        
        self.logger.info(f"Investigation logger started - Session: {timestamp}")
    
    def parse_log_line(self, line: str) -> Optional[LogEvent]:
        """Parse a single log line and extract important information"""
        if not line.strip():
            return None
        
        # Extract timestamp and level if present
        timestamp = datetime.datetime.now().isoformat()
        level = "INFO"
        
        # Try to extract timestamp from line
        timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})', line)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
        
        # Determine event type and extract relevant info
        event_type = "unknown"
        source = "autogen"
        content = line.strip()
        session_id = None
        agent_name = None
        error_info = None
        
        # Extract session ID
        session_match = self.patterns['session_id'].search(line)
        if session_match:
            session_id = session_match.group(1)
            if self.current_session is None:
                self.current_session = session_id
        
        # Extract agent name
        agent_match = self.patterns['agent_name'].search(line)
        if agent_match:
            agent_name = agent_match.group(1)
        
        # Classify event type
        if self.patterns['openai_error'].search(line):
            event_type = "openai_error"
            level = "ERROR"
            error_info = line
        elif self.patterns['error'].search(line):
            event_type = "error"
            level = "ERROR"
            error_info = line
        elif self.patterns['tool_call'].search(line):
            event_type = "tool_call"
        elif self.patterns['completion'].search(line):
            event_type = "completion"
            level = "SUCCESS"
        elif "ModelClientStreamingChunkEvent" in line:
            event_type = "streaming_chunk"
            # Extract content from streaming
            content_match = re.search(r"content['\"]:\s*['\"]([^'\"]*)['\"]", line)
            if content_match:
                content = content_match.group(1)
        elif "message handler" in line:
            event_type = "message_handler"
        elif "Publishing message" in line:
            event_type = "message_publish"
        
        return LogEvent(
            timestamp=timestamp,
            level=level,
            source=source,
            event_type=event_type,
            content=content,
            session_id=session_id,
            agent_name=agent_name,
            error_info=error_info,
            raw_message=line
        )
    
    def process_log_line(self, line: str):
        """Process a single log line and store if important"""
        event = self.parse_log_line(line)
        if event:
            # Filter out noise - only store important events
            important_types = {
                'openai_error', 'error', 'tool_call', 'completion', 
                'streaming_chunk', 'agent_communication'
            }
            
            if event.event_type in important_types or event.level in ['ERROR', 'WARNING', 'SUCCESS']:
                self.events.append(event)
                
                # Log to our structured logger (file only)
                log_level = getattr(logging, event.level, logging.INFO)
                self.logger.log(log_level, f"{event.event_type} | {event.agent_name or 'unknown'} | {event.content}")
                
                # Only critical alerts to console (very minimal)
                if event.event_type == "openai_error":
                    print("🚨 OpenAI Rate Limit Hit - Check logs")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Generate a summary of the current session"""
        if not self.events:
            return {"status": "no_events", "session_id": self.current_session}
        
        # Count events by type
        event_counts = {}
        errors = []
        last_activity = None
        
        for event in self.events:
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
            
            if event.level == 'ERROR':
                errors.append({
                    "timestamp": event.timestamp,
                    "agent": event.agent_name,
                    "error": event.error_info or event.content
                })
            
            last_activity = event.timestamp
        
        # Determine session status
        status = "unknown"
        if any(e.event_type == "completion" for e in self.events):
            status = "completed"
        elif errors:
            status = "failed_with_errors"
        elif event_counts.get("streaming_chunk", 0) > 0:
            status = "active"
        else:
            status = "starting"
        
        return {
            "session_id": self.current_session,
            "status": status,
            "total_events": len(self.events),
            "event_counts": event_counts,
            "errors": errors,
            "error_count": len(errors),
            "last_activity": last_activity,
            "has_openai_errors": any(e.event_type == "openai_error" for e in self.events)
        }
    
    def save_session_report(self) -> str:
        """Save a detailed session report"""
        summary = self.get_session_summary()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.log_dir / f"session_report_{timestamp}.json"
        
        # Prepare full report
        report = {
            "summary": summary,
            "events": [asdict(event) for event in self.events],
            "generated_at": datetime.datetime.now().isoformat()
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Session report saved: {report_file}")
        return str(report_file)
    
    def print_summary(self):
        """Print a human-readable summary"""
        summary = self.get_session_summary()
        
        print("\n" + "="*60)
        print(f"🔍 INVESTIGATION SESSION SUMMARY")
        print("="*60)
        print(f"Session ID: {summary['session_id']}")
        print(f"Status: {summary['status']}")
        print(f"Total Events: {summary['total_events']}")
        print(f"Errors: {summary['error_count']}")
        
        if summary['event_counts']:
            print(f"\nEvent Breakdown:")
            for event_type, count in summary['event_counts'].items():
                print(f"  • {event_type}: {count}")
        
        if summary['errors']:
            print(f"\n🚨 ERRORS DETECTED:")
            for i, error in enumerate(summary['errors'][:5], 1):  # Show first 5 errors
                print(f"  {i}. [{error['timestamp']}] {error.get('agent', 'unknown')}: {error['error'][:100]}...")
        
        print("="*60)

# Usage class for monitoring live logs
class LiveLogMonitor:
    def __init__(self, logger: InvestigationLogger):
        self.logger = logger
    
    def monitor_subprocess_output(self, process):
        """Monitor subprocess output and parse logs in real-time"""
        try:
            for line in iter(process.stdout.readline, b''):
                if line:
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    self.logger.process_log_line(line_str)
                    
                    # Check for critical errors (silent logging)
                    if "429" in line_str or "Too Many Requests" in line_str:
                        self.logger.save_session_report()
                        
        except Exception as e:
            self.logger.logger.error(f"Error monitoring logs: {e}")

if __name__ == "__main__":
    # Test the logger
    logger = InvestigationLogger()
    
    # Test with sample log lines
    test_lines = [
        "INFO:autogen_core:Calling message handler for SelectorGroupChatManager_97e23f35-33fc-4d8a-9b33-752c46f47f11",
        "INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions \"HTTP/1.1 429 Too Many Requests\"",
        "ERROR:autogen:Investigation failed with OpenAI rate limit",
        "INFO:autogen_core:Publishing message of type GroupChatMessage",
    ]
    
    for line in test_lines:
        logger.process_log_line(line)
    
    logger.print_summary()
    logger.save_session_report()