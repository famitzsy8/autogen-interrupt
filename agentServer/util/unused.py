"""
Unused Utility Functions
Contains functions that are not currently used in the active codebase
These functions are preserved for potential future use
"""

import pandas as pd
import json
import tiktoken
from typing import Callable, Dict, Any, Tuple, List


def get_distinct_bill_ids(csv_path: str, limit: int) -> List[str]:
    """
    Read CSV (LobbyView data) and return list of distinct bill IDs that were lobbied for.
    
    Args:
        csv_path: Path to CSV file
        limit: Maximum number of bill IDs to return
        
    Returns:
        List of distinct bill IDs
    """
    df = pd.read_csv(csv_path)
    distinct_bills = df['bill_id'].dropna().unique()
    return list(distinct_bills[:limit])


def get_bill_text_and_token_count(bill_id: str, convert_tool: Callable, extract_tool: Callable) -> Tuple[int, str]:
    """
    Process a single bill and return the number of tokens in the bill text.
    
    Args:
        bill_id: Bill identifier
        convert_tool: Function to convert bill_id to congress index
        extract_tool: Function to extract text from congress index
        
    Returns:
        Tuple of (token_count, status_message)
    """
    try:
        congress_index_result = convert_tool(bill_id)
        if not congress_index_result or not congress_index_result.get("result"):
            return 0, f"Could not convert bill_id {bill_id} to congress index. Skipping."

        congress_index = congress_index_result["result"]
        text_versions_result = extract_tool(congress_index)

        text = ""
        if text_versions_result and text_versions_result.get("text_versions"):
            text = text_versions_result["text_versions"]["text"]

        enc = tiktoken.get_encoding("cl100k_base")
        token_count = len(enc.encode(text))

        return token_count, f"Processed {bill_id}: {token_count} tokens."

    except Exception as e:
        return 0, f"Error processing {bill_id}: {str(e)}"


def write_results_to_json(data: Dict[str, Any], output_path: str):
    """
    Write dictionary to JSON file.
    
    Args:
        data: Dictionary to write
        output_path: Path to output JSON file
    """
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=4)