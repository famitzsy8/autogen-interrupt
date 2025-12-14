from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.util.split._section_split import chunk_bill

class CongressBillTextSplitter(RecursiveCharacterTextSplitter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _split_text(self, text: str, separators: List[str]) -> List[str]:

        title_chunks, text_chunks = chunk_bill(text, max_tokens=self._chunk_size)
        chunks = [c["text"] for c in text_chunks]
        # Fallback to default splitter if section-based chunking yields nothing
        if not chunks:
            print("Fallback to default splitter")
            return super()._split_text(text, separators)
        return chunks
        
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        return super().split_documents(documents)
    
    def split_text(self, text: str) -> List[str]:
        return super().split_text(text)
