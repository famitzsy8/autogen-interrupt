import pandas as pd
import json
import tiktoken
from typing import Callable, Dict, Any, Tuple, List

# Reads a CSV (our LobbyView data) and return a list of distinct bill IDs that were lobbied for
def get_distinct_bill_ids(csv_path: str, limit: int) -> List[str]:
    
    df = pd.read_csv(csv_path)
    distinct_bills = df['bill_id'].dropna().unique()
    return list(distinct_bills[:limit])

# Processes a single bill and returns the number of tokens in the bill text
def get_bill_text_and_token_count(bill_id: str, convert_tool: Callable, extract_tool: Callable) -> Tuple[int, str]:

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

# Writes a dictionary to a JSON file
def write_results_to_json(data: Dict[str, Any], output_path: str):

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=4) 