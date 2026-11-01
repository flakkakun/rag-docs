import os
from functools import cache

import psycopg
from pgvector.psycopg import register_vector

DB_URL = os.environ.get("DB_URL", "postgresql://rag:rag@localhost:5433/rag")
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Any OpenAI-compatible server works: Ollama locally (the default), vLLM, etc.
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:7b-instruct")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "ollama")   # Ollama ignores it, vLLM checks it

# bge was trained with this prefix on queries (not on documents). Leaving it off
# still works, but recall drops a little.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def connect():
    conn = psycopg.connect(DB_URL, autocommit=True)
    register_vector(conn)
    return conn


@cache
def embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


@cache
def reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(RERANK_MODEL)


@cache
def llm():
    from openai import OpenAI
    return OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def embed_docs(texts):
    return embedder().encode(texts, normalize_embeddings=True, batch_size=32)


def embed_query(text):
    return embedder().encode(QUERY_PREFIX + text, normalize_embeddings=True)
