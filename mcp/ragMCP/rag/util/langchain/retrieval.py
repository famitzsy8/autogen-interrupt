from rag.util.parse.file_parse import get_section_text
from rag.util.parse.text_parse import extract_section_number

from typing import Any
from langchain_core.runnables import RunnableSerializable
from langchain.load import dumps
from langchain_core.documents import Document


def build_full_section_context(single_retrieval_chain: RunnableSerializable[dict, Any], input_payload: dict, bill_name: str = None) -> str:
    """
    Run retrieval, extract unique section numbers, fetch full section texts, and format as a single context string.
    """
    retrieved_docs = run_retrieval_multiple_times(single_retrieval_chain, input_payload, num_runs=3, min_votes=2)

    # DISABLED Fallback: if still empty, use a single pass retrieval
    # if not retrieved_docs:
    #     try:
    #         retrieved_docs = single_retrieval_chain.invoke(input_payload)
    #     except Exception:
    #         retrieved_docs = []


    # Extract and de-duplicate section numbers while preserving order
    return _complete_docs(retrieved_docs, bill_name=bill_name)

def _complete_docs(docs: list[Document], bill_name: str = None) -> str:

    section_numbers_in_order = []

    for doc in docs:
        num = extract_section_number(doc.page_content)
        if num:
            section_numbers_in_order.append(num)
    unique_numbers = list(dict.fromkeys(section_numbers_in_order))

    sections_text_blocks = []
    for num in unique_numbers:
        full_text = get_section_text(num, bill_name=bill_name)
        if full_text:
            sections_text_blocks.append(f"SEC. {num}\n{full_text}")
    return "\n\n---\n\n".join(sections_text_blocks)

def run_retrieval_multiple_times(single_retrieval_chain: RunnableSerializable[dict, Any], input_payload: dict, num_runs: int = 3, min_votes: int = 2) -> list[Document]:

    runs_documents = []
    
    for _ in range(num_runs):
        docs_once = single_retrieval_chain.invoke(input_payload)
        runs_documents.append(docs_once)

    aggregated = _aggregate_docs_across_runs(runs_documents, min_votes=min_votes)
    return aggregated

def _aggregate_docs_across_runs(runs_documents: list[list[Document]], min_votes: int = 2) -> list[Document]:
    """Return documents that appear in at least `min_votes` of the runs.
    Uses serialized `Document` objects as stable keys for counting frequency.
    """
    frequency_by_doc_key = {}
    first_seen_doc_by_key = {}
    for docs_in_run in runs_documents:
        # Ensure a document is only counted once per run
        seen_this_run = set()
        for doc in docs_in_run:
            key = dumps(doc)
            if key in seen_this_run:
                continue
            seen_this_run.add(key)
            frequency_by_doc_key[key] = frequency_by_doc_key.get(key, 0) + 1
            if key not in first_seen_doc_by_key:
                first_seen_doc_by_key[key] = doc
    return [first_seen_doc_by_key[k] for k, count in frequency_by_doc_key.items() if count >= min_votes]
