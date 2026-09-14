"""Retrieval-Augmented Generation knowledge-base layer for Singapore."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = ""
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

DATA_SOURCES = [
    {
        "path": DATA_DIR / "wikivoyage_singapore.txt",
        "title": "Wikivoyage Singapore Travel Guide",
        "url": "https://en.wikivoyage.org/wiki/Singapore",
    },
    {
        "path": DATA_DIR / "visit_singapore_essential.txt",
        "title": "Visit Singapore: Essential Visitor Information",
        "url": "https://www.visitsingapore.com/travel-guide-tips/essential-information/",
    },
    {
        "path": DATA_DIR / "visit_singapore_itineraries.txt",
        "title": "Visit Singapore: Sample Itineraries",
        "url": "https://www.visitsingapore.com/itineraries/",
    },
]

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 4
RELEVANCE_THRESHOLD = 0.30


def _validate_sources() -> None:
    missing = [str(source["path"]) for source in DATA_SOURCES if not source["path"].exists()]
    if missing:
        raise FileNotFoundError(
            "Knowledge-base files are missing:\n- " + "\n- ".join(missing)
        )


@lru_cache(maxsize=1)
def get_vectorstore() -> FAISS:
    """Load, chunk, embed and index the three supplied public sources once."""
    _validate_sources()

    documents = []
    for source in DATA_SOURCES:
        loader = TextLoader(str(source["path"]), encoding="utf-8")
        docs = loader.load()
        for doc in docs:
            doc.metadata.update(
                {
                    "source_title": source["title"],
                    "source_url": source["url"],
                    "source_file": source["path"].name,
                }
            )
            documents.append(doc)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu", "token": HF_TOKEN},
        encode_kwargs={"normalize_embeddings": True},
    )
    return FAISS.from_documents(chunks, embeddings)


def retrieve_knowledge(query: str, k: int = TOP_K):
    """Return only reasonably relevant semantic matches with their scores."""
    vectorstore = get_vectorstore()
    matches = vectorstore.similarity_search_with_relevance_scores(query, k=k)
    return [
        (doc, float(score))
        for doc, score in matches
        if float(score) >= RELEVANCE_THRESHOLD
    ]


def get_retriever():
    """Compatibility helper for code that needs a LangChain retriever."""
    return get_vectorstore().as_retriever(search_kwargs={"k": TOP_K})
