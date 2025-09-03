#!/usr/bin/env python3
"""
Silent buffer-based logging system
- NO console output during runtime
- Buffers ALL logs in memory
- Writes buffer to file ONLY at shutdown
"""

import logging
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from collections import deque
import json
import re

class SilentBufferLogger:
    """Captures all logs silently in buffer, writes at shutdown only"""
    
    def __init__(self, log_dir="logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # In-memory buffer for all log messages
        self.message_buffer = []
        self.buffer_lock = threading.Lock()
        
        # Session info
        self.start_time = datetime.now()
        self.session_id = self.start_time.strftime("%Y%m%d_%H%M%S")
        
        # Stats tracking
        self.stats = {
            'total_messages': 0,
            'openai_errors': 0,
            'tool_calls': 0,
            'errors': 0,
            'warnings': 0,
            'info': 0
        }
        
        # Message classification patterns
        self.patterns = {
            'openai_error': re.compile(r'(429|Too Many Requests|rate limit|Retrying request)', re.IGNORECASE),
            'tool_call': re.compile(r'(tool_call|ToolCallEvent|execute_function|calling function)', re.IGNORECASE),
            'error': re.compile(r'(ERROR|Exception|Traceback|Failed)', re.IGNORECASE),
            'warning': re.compile(r'(WARNING|WARN)', re.IGNORECASE)
        }
        
        # Setup silent logging capture
        self.setup_silent_capture()
        
        # ONLY print startup message, then go silent
        print(f"🔇 Silent logging active - buffer mode")
        print(f"📁 Will write to: logs/silent_autogen_{self.session_id}.log")
        print("🤐 Console output suppressed during runtime")
    
    def setup_silent_capture(self):
        """Setup completely silent logging capture"""
        
        class SilentHandler(logging.Handler):
            def __init__(self, logger_instance):
                super().__init__()
                self.logger_instance = logger_instance
                # Set to capture everything
                self.setLevel(logging.DEBUG)
            
            def emit(self, record):
                try:
                    # Format the message
                    message = self.format(record)
                    # Send to buffer (NO console output)
                    self.logger_instance.buffer_message(message, record.levelname, record.name)
                except Exception:
                    # Completely silent - no error output
                    pass
        
        # Create our silent handler
        silent_handler = SilentHandler(self)
        silent_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        ))
        
        # Capture ALL Python logging
        root_logger = logging.getLogger()
        root_logger.handlers.clear()  # Remove all existing handlers
        root_logger.addHandler(silent_handler)
        root_logger.setLevel(logging.DEBUG)
        
        # Specific loggers to ensure we catch everything
        logger_names = [
            'openai', 'websockets',
            'asyncio', 'urllib3', 'requests', 'aiohttp', 'autogen_server'
        ]
        
        for name in logger_names:
            logger = logging.getLogger(name)
            logger.handlers.clear()
            logger.addHandler(silent_handler)
            logger.setLevel(logging.DEBUG)
            logger.propagate = False  # Don't propagate to root
        
        # Also redirect stdout/stderr to capture print statements
        self.setup_stdout_capture()
    
    def setup_stdout_capture(self):
        """Capture stdout/stderr to buffer instead of console"""
        class BufferWriter:
            def __init__(self, logger_instance, stream_name):
                self.logger_instance = logger_instance
                self.stream_name = stream_name
                self.original_stream = getattr(sys, stream_name)
            
            def write(self, text):
                if text.strip():  # Only capture non-empty output
                    self.logger_instance.buffer_message(
                        text.strip(), 
                        'ERROR' if self.stream_name == 'stderr' else 'INFO',
                        f'captured_{self.stream_name}'
                    )
                # Also write to original stream for critical messages
                if ('🚀' in text or '📍' in text or '🔇' in text or '📁' in text or '🤐' in text):
                    self.original_stream.write(text)
                    self.original_stream.flush()
            
            def flush(self):
                pass
        
        # Redirect stdout and stderr
        sys.stdout = BufferWriter(self, 'stdout')
        sys.stderr = BufferWriter(self, 'stderr')
    
    def buffer_message(self, message, level, logger_name):
        """Add message to buffer with content extraction and filtering (completely silent)"""
        try:
            with self.buffer_lock:
                # Extract actual content from the message
                extracted_content = self.extract_message_content(message, logger_name)
                
                # Skip if no meaningful content after extraction
                if not extracted_content or self.should_skip_message(extracted_content, logger_name):
                    return
                
                # Classify the extracted content
                msg_type = self.classify_message(extracted_content)
                
                # Update stats
                self.stats['total_messages'] += 1
                if msg_type in self.stats:
                    self.stats[msg_type] += 1
                elif level.upper() in ['INFO', 'DEBUG']:
                    self.stats['info'] += 1
                
                # Create enhanced buffer entry
                entry = {
                    'timestamp': datetime.now().isoformat(),
                    'level': level,
                    'logger': logger_name,
                    'type': msg_type,
                    'content': extracted_content,
                    'raw_message': message if extracted_content != message else None
                }
                
                self.message_buffer.append(entry)
                
        except Exception:
            # Completely silent - no error handling output
            pass
    
    def extract_message_content(self, message, logger_name):
        """Extract actual content from log messages, removing prefixes and metadata"""
        try:
            # If it's already clean content, return as-is
            if logger_name in ['captured_stdout', 'captured_stderr']:
                return message.strip()
            
            # Remove timestamp prefixes like "2025-08-17 14:30:15,123 | INFO | autogen | "
            content = re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\s*\|\s*\w+\s*\|\s*\w+\s*\|\s*', '', message)
            
            # Remove additional AutoGen prefixes
            content = re.sub(r'^INFO:autogen[^:]*:\s*', '', content)
            content = re.sub(r'^DEBUG:autogen[^:]*:\s*', '', content)
            content = re.sub(r'^WARNING:autogen[^:]*:\s*', '', content)
            content = re.sub(r'^ERROR:autogen[^:]*:\s*', '', content)
            
            # Remove HTTP request prefixes but keep the important part
            if 'HTTP Request:' in content:
                # Keep HTTP errors, skip successful requests
                if '200' in content or '201' in content:
                    return None  # Skip successful HTTP requests
                # Keep errors and rate limits
                content = re.sub(r'^.*HTTP Request:\s*', 'HTTP Request: ', content)
            
            # Extract AutoGen agent communications
            if any(agent in content.lower() for agent in ['orchestrator', 'committee_specialist', 'bill_specialist', 'actions_specialist', 'amendment_specialist', 'congress_member_specialist']):
                # This looks like agent communication - keep it all
                return content.strip()
            
            # Extract tool calls and results
            if any(keyword in content.lower() for keyword in ['tool_call', 'execute_function', 'function_result']):
                return content.strip()
            
            # Extract investigation status messages
            if any(keyword in content.lower() for keyword in ['investigation', 'starting', 'complete', 'concluded', 'terminate']):
                return content.strip()
            
            # Extract errors and important warnings
            if any(keyword in content.lower() for keyword in ['error', 'exception', 'failed', 'traceback', '429', 'rate limit']):
                return content.strip()
            
            # For other messages, clean and return if substantial
            cleaned = content.strip()
            if len(cleaned) > 10:  # Only keep messages with some substance
                return cleaned
            
            return None
            
        except Exception:
            # If extraction fails, return original message
            return message.strip() if message else None
    
    def should_skip_message(self, content, logger_name):
        """Determine if a message should be skipped from the buffer"""
        try:
            if not content or len(content.strip()) < 5:
                return True
            
            content_lower = content.lower()
            
            # Skip common noise
            noise_patterns = [
                'starting',
                'ready',
                'listening',
                'connected',
                'disconnected',
                'received ping',
                'sent pong',
                'heartbeat',
                'keepalive',
                'health check'
            ]
            
            for pattern in noise_patterns:
                if pattern in content_lower and len(content) < 50:
                    return True
            
            # Skip repetitive HTTP success messages
            if 'http/1.1 200' in content_lower or 'http/1.1 201' in content_lower:
                return True
            
            # Skip verbose websocket messages unless they're errors
            if 'websocket' in content_lower and 'error' not in content_lower and 'failed' not in content_lower:
                return True
            
            # Skip asyncio debug messages
            if logger_name == 'asyncio' and 'debug' in content_lower:
                return True
            
            return False
            
        except Exception:
            return False  # When in doubt, keep the message
    
    def classify_message(self, message):
        """Classify message type"""
        try:
            for msg_type, pattern in self.patterns.items():
                if pattern.search(message):
                    return msg_type
            return 'info'
        except Exception:
            return 'unknown'
    
    def write_buffer_to_file(self):
        """Write entire buffer to file at shutdown"""
        try:
            # Generate final log file
            log_file = self.log_dir / f"silent_autogen_{self.session_id}.log"
            
            # Calculate session duration
            end_time = datetime.now()
            duration = (end_time - self.start_time).total_seconds()
            
            # Create session metadata
            session_info = {
                'session_id': self.session_id,
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'total_messages': len(self.message_buffer),
                'stats': self.stats
            }
            
            with open(log_file, 'w', encoding='utf-8') as f:
                # Write session header
                f.write("=== SILENT AUTOGEN SESSION LOG ===\n")
                f.write(f"Session: {self.session_id}\n")
                f.write(f"Duration: {duration:.1f} seconds\n")
                f.write(f"Total Messages: {len(self.message_buffer)}\n")
                f.write(f"OpenAI Errors: {self.stats['openai_errors']}\n")
                f.write(f"Tool Calls: {self.stats['tool_calls']}\n")
                f.write(f"Errors: {self.stats['errors']}\n")
                f.write(f"Warnings: {self.stats['warnings']}\n")
                f.write("=" * 50 + "\n\n")
                
                # Write session metadata as JSON
                f.write("SESSION_METADATA: " + json.dumps(session_info) + "\n\n")
                
                # Write filtered and cleaned messages
                f.write("=== FILTERED AUTOGEN CONTENT ===\n\n")
                
                for entry in self.message_buffer:
                    # Write in a more readable format
                    f.write(f"[{entry['timestamp']}] [{entry['level']}] [{entry['type'].upper()}]\n")
                    f.write(f"Logger: {entry['logger']}\n")
                    f.write(f"Content: {entry['content']}\n")
                    if entry.get('raw_message') and entry['raw_message'] != entry['content']:
                        f.write(f"Raw: {entry['raw_message']}\n")
                    f.write("\n" + "-"*80 + "\n\n")
            
            # Print final summary (ONLY thing printed during shutdown)
            print(f"\n📊 SESSION COMPLETE")
            print(f"Duration: {duration:.1f}s | Messages: {len(self.message_buffer)} | Errors: {self.stats['openai_errors']}")
            print(f"📁 Full log saved: {log_file}")
            
            return str(log_file)
            
        except Exception as e:
            print(f"Error writing log file: {e}")
            return None
    
    def get_stats(self):
        """Get current session statistics"""
        return {
            'session_id': self.session_id,
            'duration': (datetime.now() - self.start_time).total_seconds(),
            'buffer_size': len(self.message_buffer),
            'stats': self.stats.copy()
        }

# Global logger instance
_global_logger = None

def setup_silent_logging():
    """Setup silent buffer-based logging"""
    global _global_logger
    if _global_logger is None:
        _global_logger = SilentBufferLogger()
    return _global_logger

def shutdown_logging():
    """Write buffer to file and cleanup"""
    global _global_logger
    if _global_logger:
        return _global_logger.write_buffer_to_file()
    return None

if __name__ == "__main__":
    # Test the silent logger
    logger = setup_silent_logging()
    
    import logging
    test_logger = logging.getLogger('test')
    test_logger.info("This should be silent")
    test_logger.error("This should also be silent")
    
    print("Testing...")  # This should be captured
    time.sleep(1)
    
    # Shutdown test
    log_file = shutdown_logging()
    print(f"Test complete: {log_file}")