import re
from typing import List

from rag.util.token.token import get_token_encoder

_ENCODER = get_token_encoder()

def _token_count(text: str) -> int:
    return len(_ENCODER.encode(text))


# removes the text between <DELETED> and </DELETED> tags that indicate overwritten text in a bill
def remove_deleted_text(text: str) -> str:
    return re.sub(r"<DELETED>.*?</DELETED>", "", text, flags=re.DOTALL)

# this function is used to compress a list of numbers into a string of ranges
# e.g. [1, 2, 3, 5, 6, 7, 8, 10] -> "1-3, 5-8, 10"
def _compress_numbers(nums: List[int]) -> str:
    if not nums: return ""
    nums = sorted(set(nums))
    ranges, start = [], nums[0]
    for i in range(1, len(nums)):
        if nums[i] != nums[i-1] + 1:
            ranges.append(f"{start}-{nums[i-1]}" if start != nums[i-1] else f"{start}")
            start = nums[i]
    ranges.append(f"{start}-{nums[-1]}" if start != nums[-1] else f"{start}")
    return ", ".join(ranges)


# returns a list of text chunks that are no more than tokens_per_chunk tokens long, with specified overlap (in tokens)
def _fixed_size_chunk(text: str, tokens_per_chunk: int, overlap: int = 0) -> List[str]:
    # Normalize inputs to integers and support fractional overlaps (e.g., 0.15)
    if tokens_per_chunk <= 0:
        raise ValueError("tokens_per_chunk must be positive")

    # Allow overlap to be specified as a fraction (<1) or absolute token count (>=1)
    if isinstance(overlap, float) and 0 < overlap < 1:
        overlap_tokens = int(tokens_per_chunk * overlap)
    else:
        overlap_tokens = int(overlap)

    tokens_per_chunk = int(tokens_per_chunk)

    # Ensure overlap is within valid bounds
    if overlap_tokens >= tokens_per_chunk:
        overlap_tokens = max(0, tokens_per_chunk - 1)

    tokens = _ENCODER.encode(text)
    chunks: List[str] = []
    i = 0
    step = max(1, tokens_per_chunk - overlap_tokens)
    while i < len(tokens):
        chunk = tokens[i : i + tokens_per_chunk]
        chunks.append(_ENCODER.decode(chunk))
        if i + tokens_per_chunk >= len(tokens):
            break
        i += step
    return chunks

# extracts the section number from a string
def extract_section_number(text: str):
    match = re.search(r"\b(?:SEC|Sec|Section)\.?\s*(\d+)", text, flags=re.IGNORECASE)
    return match.group(1) if match else None