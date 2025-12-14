import os
from langchain.load import dumps, loads
from typing import Any

from langchain_core.runnables import RunnableSerializable
from langchain_core.vectorstores.base import VectorStoreRetriever

local_path = os.path.dirname(os.path.abspath(__file__))

def log_queries(queries: list[str]) -> list[str]:
    print("Generated queries:")
    for i, q in enumerate(queries, 1):
        print(f"[{i}] {q}")
    return queries

def get_unique_union(documents: list[list]):
    """ Unique union of retrieved docs """
    flattened_docs = [dumps(doc) for sublist in documents for doc in sublist]
    unique_docs = list(set(flattened_docs))
    return [loads(doc) for doc in unique_docs]

def get_single_retrieval_chain(generate_queries: RunnableSerializable[dict, Any], retriever: VectorStoreRetriever):
    a = (generate_queries | log_queries | retriever.map() | get_unique_union)
    return a