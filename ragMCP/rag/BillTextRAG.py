import os
from operator import itemgetter
from typing import Optional

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from rag.util.split.CongressBillTextSplitter import CongressBillTextSplitter
from rag.util.parse.file_parse import load_prompts
from rag.util.langchain.retrieval import build_full_section_context, _complete_docs
from rag.util.langchain.lang import get_single_retrieval_chain
from rag.util.api.authenticate import _get_key

oai_key = _get_key("OPENAI_API_KEY")
langsmith_key = _get_key("LANGCHAIN_API_KEY")

class BillTextRAG:

    def __init__(self, 
        bill_name: str, 
        collection_name: str = "langchain", 
        langsmith_tracing: bool = False) -> None:

        os.environ["OPENAI_API_KEY"] = oai_key

        if langsmith_tracing:
            os.environ['LANGCHAIN_TRACING_V2'] = 'true'
            os.environ['LANGCHAIN_ENDPOINT'] = 'https://api.smith.langchain.com'
            os.environ['LANGCHAIN_API_KEY'] = langsmith_key

        self.bill_name = bill_name
        self.collection_name = collection_name
        self.path = os.path.dirname(os.path.abspath(__file__))
        
        self.embeddings = OpenAIEmbeddings()

        # Here we create the directory that stores the embedding vectors for the bill passed
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.persist_directory = os.path.join(
            base_dir, "vectorstores", "chroma_congress_bills", bill_name
        )
        os.makedirs(self.persist_directory, exist_ok=True)

        self.vectorstore: Optional[Chroma] = None
        self.retriever = None

    def _load_or_build_vectorstore(self) -> Chroma:
        chroma_db_file = os.path.join(self.persist_directory, "chroma.sqlite3")
        if os.path.exists(chroma_db_file):
            return Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name=self.collection_name,
            )

        loader = TextLoader(f"{self.path}/data/bill_texts/{self.bill_name}.txt")
        docs = loader.load()
        text_splitter = CongressBillTextSplitter(chunk_size=250, chunk_overlap=200)
        chunks = text_splitter.split_documents(docs)

        if not chunks:
            raise ValueError(f"No chunks produced from bill text '{self.bill_name}.txt'. Check text extraction and splitting.")

        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=self.persist_directory,
            collection_name=self.collection_name,
        )
        try:
            vectorstore.persist()
        except Exception:
            pass
        return vectorstore

    def get_retriever(self):
        if self.vectorstore is None:
            self.vectorstore = self._load_or_build_vectorstore()
        if self.retriever is None:
            self.retriever = self.vectorstore.as_retriever()
        return self.retriever

    def _setup_rag_chain(self, company_name: str, bill_text: str, bill_summary_text: str):
        
        with open(f"{self.path}/data/bill_texts/{self.bill_name}.txt", "w") as f:
            f.write(bill_text)

        with open(f"{self.path}/data/bill_summaries/{self.bill_name}_summary.txt", "w") as f:
            f.write(bill_summary_text)

        self.prompts = load_prompts()

        self.lobbying_strategy_prompt = ChatPromptTemplate.from_template(
            self.prompts["lobbying_strategy_generator_prompt"]
        )
        self.report_generator_prompt = ChatPromptTemplate.from_template(
            self.prompts["report_generator_prompt"]
        )

        self.generate_queries = (
            self.lobbying_strategy_prompt
            | ChatOpenAI(model="gpt-4o")
            | StrOutputParser()
            | (lambda x: x.split("\n"))
        )

        self.get_retriever()

        self.single_retrieval_chain = get_single_retrieval_chain(self.generate_queries, self.retriever)

        self.llm = ChatOpenAI(model="gpt-4o")


    def run_relevant_sections(self, company_name: str, bill_text: str, bill_summary_text: str) -> str:

        self._setup_rag_chain(company_name, bill_text, bill_summary_text)

        # Only retrieve the relevant sections from the index (no further processing)
        final_rag_chain = self.single_retrieval_chain

        docs = final_rag_chain.invoke(
            {
                "company_name": company_name,
                "summary": bill_summary_text,
                "bill_name": self.bill_name
            }
        )
        return _complete_docs(docs)
        

    def run_report(self, company_name: str, bill_text: str, bill_summary_text: str) -> str:

        self._setup_rag_chain(company_name, bill_text, bill_summary_text)

        final_rag_chain = (
            {
                "context": lambda x: build_full_section_context(
                    self.single_retrieval_chain, x
                ),
                "company_name": itemgetter("company_name"),
                "summary": itemgetter("summary"),
                "bill_name": itemgetter("bill_name"),
            }
            | self.report_generator_prompt
            | self.llm
            | StrOutputParser()
        )

        return final_rag_chain.invoke(
            {
                "company_name": company_name,
                "summary": bill_summary_text,
                "bill_name": self.bill_name,
            }
        )