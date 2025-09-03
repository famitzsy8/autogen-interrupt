"""
LLM Summarization utilities for AutoGen communications and tool results.
"""

import openai
import configparser
import os
from pathlib import Path

class LLMSummarizer:
    def __init__(self):
        self.client = None
        self._load_api_key()
    
    def _load_api_key(self):
        """Load OpenAI API key from secrets.ini"""
        try:
            config = configparser.ConfigParser()
            # Try multiple possible locations
            secrets_paths = [
                "/app/secrets.ini",
                "/app/agentServer/secrets.ini",
                "secrets.ini",
                Path(__file__).parent / "secrets.ini",
                Path(__file__).parent.parent / "secrets.ini"
            ]
            
            api_key = None
            for path in secrets_paths:
                if os.path.exists(str(path)):
                    config.read(str(path))
                    try:
                        # Use the correct section and key names
                        api_key = config["API_KEYS"]["OPENAI_API_KEY"]
                        print(f"✅ LLM Summarizer: Found API key in {path}")
                        break
                    except KeyError:
                        continue
            
            if api_key:
                self.client = openai.OpenAI(api_key=api_key)
                print("✅ LLM Summarizer: Initialized successfully")
            else:
                print("⚠️  LLM Summarizer: API key not found, summarization disabled")
        except Exception as e:
            print(f"❌ LLM Summarizer: Error loading API key: {e}")
    
    async def summarize_agent_communication(self, agent_name: str, full_content: str) -> str:
        """
        Generate a very concise summary of agent communication (10 tokens max) for the UI box display.
        """
        if not self.client:
            # Return first 50 characters as fallback
            return full_content[:50] + "..." if len(full_content) > 50 else full_content
        
        try:
            prompt = f"""
            Summarize what happened in the following communication: \n
            {full_content[:max(len(full_content) - 1, 800)]} \n
            It is important to remember that we are summarizing this for a political scientist
            that needs a concise summary of what the AI agents are doing.

            Return a summary of EXACTLY 20 tokens or less
            """

            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a concise summarizer. Respond with EXACTLY 10 tokens or less. Focus on the main action or finding."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=20,  # Reduced to enforce brevity
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            # Ensure it fits in the box
            if len(summary) > 200:
                summary = summary[:197] + "..."
            
            return summary
            
        except Exception as e:
            print(f"Error summarizing agent communication: {e}")
            return full_content[:200] + "..." if len(full_content) > 200 else full_content
    
    async def summarize_tool_call_result(self, tool_name: str, result_content: str) -> str:
        """
        Generate a 5-word summary of tool call results for the loading box.
        """
        if not self.client:
            return f"{tool_name} completed"
        
        try:
            prompt = f"""Summarize this tool call result in exactly 5 words for a dashboard:

Tool: {tool_name}
Result: {result_content[:500]}

Examples:
- "Found 3 committee members data"
- "Retrieved bill sponsor information"  
- "Extracted 5 relevant sections"
- "Error: missing required parameters"

5-word summary:"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You summarize tool results in exactly 5 words. Be specific about numbers and outcomes."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=20,
                temperature=0.1
            )
            
            summary = response.choices[0].message.content.strip()
            # Ensure it's roughly 8 words
            words = summary.split()
            if len(words) > 8:
                summary = " ".join(words[:7])
            
            return summary
            
        except Exception as e:
            print(f"Error summarizing tool result: {e}")
            return f"{tool_name} completed"
    
    async def parse_tool_call_details(self, tool_name: str, arguments: dict, result_content: str) -> dict:
        """
        Parse tool call results into structured format for detailed display.
        """
        if not self.client:
            return {
                "summary": f"{tool_name} executed",
                "key_findings": ["Tool execution completed"],
                "data_points": len(str(result_content).split('\n')),
                "success": True
            }
        
        try:
            prompt = f"""Parse this tool call result for a lobbying investigation dashboard:

Tool: {tool_name}
Arguments: {arguments}
Result: {result_content[:5000]}

Extract:
1. Brief summary (1 sentence)
2. Key findings (3-5 bullet points)
3. Number of data points found
4. Success status

Format as JSON:
{{
  "summary": "Brief summary sentence",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
  "data_points": 5,
  "success": true
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You extract structured data from tool call results. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            import json
            result = json.loads(response.choices[0].message.content.strip())
            return result
            
        except Exception as e:
            print(f"Error parsing tool call details: {e}")
            return {
                "summary": f"{tool_name} executed with results",
                "key_findings": ["Results retrieved successfully"],
                "data_points": len(str(result_content).split('\n')),
                "success": "error" not in result_content.lower()
            }