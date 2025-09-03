#!/usr/bin/env python3
"""
Real-time logging system that actually captures AutoGen output
This replaces the broken subprocess-based approach
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

class ThrottledConsoleHandler:
    """Console handler that only prints one message per second"""
    
    def __init__(self, interval=1.0):
        self.interval = interval
        self.last_print = 0
        self.message_queue = deque(maxlen=1000)  # Keep last 1000 messages
        self.lock = threading.Lock()
        
    def log(self, message):
        with self.lock:
            self.message_queue.append({
                'timestamp': datetime.now().isoformat(),
                'message': str(message)
            })
            
            current_time = time.time()
            if current_time - self.last_print >= self.interval:
                self._print_latest()
                self.last_print = current_time
    
    def _print_latest(self):
        if self.message_queue:
            latest = self.message_queue[-1]
            print(f"[{latest['timestamp']}] {latest['message']}")
    
    def get_recent_messages(self, count=10):
        """Get recent messages for debugging"""
        with self.lock:
            return list(self.message_queue)[-count:]

class RealTimeAutogenLogger:
    """Captures all AutoGen logs in real-time without subprocess"""
    
    def __init__(self, log_dir="logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup file logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"autogen_realtime_{timestamp}.log"
        
        # Setup throttled console
        self.console = ThrottledConsoleHandler(interval=1.0)
        
        # Message patterns for classification
        self.patterns = {
            'openai_error': re.compile(r'(429|Too Many Requests|rate limit|Retrying request)', re.IGNORECASE),
            'tool_call': re.compile(r'(tool_call|ToolCallEvent|execute_function)', re.IGNORECASE),
            'agent_communication': re.compile(r'(agent|message|communication|orchestrator)', re.IGNORECASE),
            'error': re.compile(r'(ERROR|Exception|Traceback|Failed)', re.IGNORECASE),
            'warning': re.compile(r'(WARNING|WARN)', re.IGNORECASE)
        }
        
        # Statistics
        self.stats = {
            'total_messages': 0,
            'openai_errors': 0,
            'tool_calls': 0,
            'errors': 0,
            'warnings': 0,
            'start_time': datetime.now()
        }
        
        # Setup Python logging capture
        self.setup_logging_capture()
        
        print(f"🚀 Real-time AutoGen logger started")
        print(f"📁 Logs: {self.log_file}")
        print(f"🔇 Console throttled to 1 message/second")
        print("=" * 50)
    
    def setup_logging_capture(self):
        """Intercept all Python logging output"""
        
        # Create custom handler that captures everything
        class CaptureHandler(logging.Handler):
            def __init__(self, logger_instance):
                super().__init__()
                self.logger_instance = logger_instance
            
            def emit(self, record):
                try:
                    message = self.format(record)
                    self.logger_instance.process_log_message(message, record.levelname)
                except Exception:
                    pass  # Don't let logging errors crash the app
        
        # Add our capture handler to root logger
        capture_handler = CaptureHandler(self)
        capture_handler.setLevel(logging.DEBUG)
        capture_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        ))
        
        # Add to all relevant loggers
        loggers_to_capture = [
            'autogen',
            'autogen_core', 
            'httpx',
            'openai',
            'websockets',
            'asyncio',
            'root'
        ]
        
        for logger_name in loggers_to_capture:
            logger = logging.getLogger(logger_name)
            logger.addHandler(capture_handler)
            logger.setLevel(logging.DEBUG)
        
        # Also capture root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(capture_handler)
        root_logger.setLevel(logging.DEBUG)
    
    def process_log_message(self, message, level):
        """Process a single log message"""
        try:
            self.stats['total_messages'] += 1
            
            # Classify message
            message_type = self.classify_message(message)
            
            # Update stats
            if message_type == 'openai_error':
                self.stats['openai_errors'] += 1
            elif message_type == 'tool_call':
                self.stats['tool_calls'] += 1
            elif message_type == 'error':
                self.stats['errors'] += 1
            elif message_type == 'warning':
                self.stats['warnings'] += 1
            
            # Create log entry
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'type': message_type,
                'message': message,
                'session_stats': self.stats.copy()
            }
            
            # Write to file immediately
            self.write_to_file(log_entry)
            
            # Show in throttled console
            console_msg = f"[{message_type.upper()}] {message[:100]}{'...' if len(message) > 100 else ''}"
            self.console.log(console_msg)
            
            # Special handling for critical errors
            if message_type == 'openai_error':
                self.console.log(f"🚨 OpenAI Rate Limit Hit! Total: {self.stats['openai_errors']}")
            
        except Exception as e:
            # Don't let logging errors crash the application
            print(f"Logging error: {e}")
    
    def classify_message(self, message):
        """Classify message type based on content"""
        message_lower = message.lower()
        
        for msg_type, pattern in self.patterns.items():
            if pattern.search(message):
                return msg_type
        
        return 'info'
    
    def write_to_file(self, log_entry):
        """Write log entry to file"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
                f.flush()  # Ensure immediate write
        except Exception as e:
            print(f"File write error: {e}")
    
    def get_session_summary(self):
        """Get summary of current session"""
        duration = datetime.now() - self.stats['start_time']
        return {
            'duration_seconds': duration.total_seconds(),
            'total_messages': self.stats['total_messages'],
            'openai_errors': self.stats['openai_errors'], 
            'tool_calls': self.stats['tool_calls'],
            'errors': self.stats['errors'],
            'warnings': self.stats['warnings'],
            'messages_per_second': self.stats['total_messages'] / max(duration.total_seconds(), 1),
            'log_file': str(self.log_file)
        }
    
    def print_summary(self):
        """Print session summary"""
        summary = self.get_session_summary()
        print("\n" + "="*60)
        print("📊 AUTOGEN SESSION SUMMARY")
        print("="*60)
        print(f"Duration: {summary['duration_seconds']:.1f} seconds")
        print(f"Total Messages: {summary['total_messages']}")
        print(f"Messages/sec: {summary['messages_per_second']:.1f}")
        print(f"OpenAI Errors: {summary['openai_errors']}")
        print(f"Tool Calls: {summary['tool_calls']}")
        print(f"Errors: {summary['errors']}")
        print(f"Warnings: {summary['warnings']}")
        print(f"Log File: {summary['log_file']}")
        print("="*60)

# Global logger instance
_global_logger = None

def get_logger():
    """Get or create global logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = RealTimeAutogenLogger()
    return _global_logger

def setup_autogen_logging():
    """Setup AutoGen logging capture - call this before starting server"""
    return get_logger()

if __name__ == "__main__":
    # Test the logger
    logger = setup_autogen_logging()
    
    # Simulate some log messages
    import logging
    test_logger = logging.getLogger('autogen')
    
    print("Testing logger...")
    test_logger.info("Test info message")
    test_logger.error("Test error message")
    test_logger.warning("HTTP Request: POST https://api.openai.com/v1/chat/completions \"HTTP/1.1 429 Too Many Requests\"")
    
    time.sleep(2)
    logger.print_summary()