"""Prompts for analysis component parsing and message scoring.

These prompts are used by the Analysis Watchlist System to:
- Parse user descriptions into structured analysis criteria
- Score agent messages against trusted facts for hallucination detection

All prompts use string templates for .format() calls.
"""

COMPONENT_PARSING_PROMPT = """Extract 2-5 structured criteria from this user description of what to watch for.

User description:
{analysis_prompt}

Return JSON with criteria, each having:
- label: 2-3 word kebab-case identifier (e.g., "committee-membership")
- description: 1-2 sentence explanation of what to check

Format your response as valid JSON only, no other text.

Example:
{{
  "components": [
    {{
      "label": "committee-membership",
      "description": "Verify that committee member names match API data..."
    }}
  ]
}}
"""

MESSAGE_SCORING_PROMPT = """Analyze this agent message for accuracy and consistency against known facts.

=== TRUSTED FACTS (from verified tool calls) ===
{tool_call_facts}

=== AGENT'S CLAIM (what to verify) ===
{agent_message}

=== RESEARCH CONTEXT (for reference) ===
{state_of_run}

=== CRITERIA TO SCORE ===
{components_description}

For each criterion, score 1-10:
- 1-3: Claim is fully supported by trusted facts
- 4-7: Claim makes unverified assertions (not in trusted facts)
- 8-10: Claim contradicts trusted facts or shows hallucination

Only include reasoning if score >= {trigger_threshold}.
Return valid JSON only, no other text.

Example format:
{{{{
  "scores": {{{{
    "committee-membership": {{{{"score": 9, "reasoning": "Claimed Jane Smith is ranking member but API shows John Doe"}}}},
    "geographic-hallucination": {{{{"score": 3, "reasoning": ""}}}}
  }}}}
}}}}
"""
