# RAG Retrieval: Hybrid Search + Reranking, Measured

Finds the passages in a folder of documents that best answer a question, and measures how often it gets the right one. Answer generation is the next step; this repo is about the part that decides answer quality: retrieval.

## How it works

```
                 ┌─▶ vector search (HNSW index, top 50) ──┐
question ──embed─┤                                         ├─▶ RRF merge ─▶ cross-encoder rerank (top 30) ─▶ top 5
                 └─▶ keyword search (full-text, top 50) ──┘
```

| Stage | What it does | Why |
|---|---|---|
| **Chunking** | Packs whole paragraphs into ~1,200-character chunks, repeating one paragraph between neighbours | Whole documents are too big to match precisely; overlap keeps ideas that cross a boundary intact |
| **Embedding** | `bge-small-en-v1.5` turns each chunk into 384 numbers | Similar meaning → nearby vectors |
| **Vector search** | pgvector **HNSW** index, `ef_search` = 100 | Finds near neighbours without scanning every vector; approximate, so `ef_search` trades recall for speed |
| **Keyword search** | Postgres full-text search (GIN index) | Embeddings are weak on exact terms: names, codes, numbers |
| **RRF** | Merges both lists by rank: `score = Σ 1/(60 + rank)` | The two searches score on different scales; ranks don't care |
| **Rerank** | `ms-marco-MiniLM-L-6` cross-encoder reads question + chunk together | More accurate than comparing vectors, too slow to run on everything |

Everything runs locally: Postgres + pgvector in Docker, models on CPU/Apple Silicon. No API keys.

## Run it

```bash
docker compose up -d                       # Postgres + pgvector on port 5433
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -r requirements.txt

cp your-notes/*.md data/                   # any .md / .txt files
python ingest.py                           # chunk, embed, store
python search.py "your question"           # --mode vector|keyword|hybrid|rerank
python eval.py                             # recall@5 for each mode
```

## Evaluation

`eval/questions.jsonl` holds test questions, each with a short phrase that the right passage contains. A hit means that phrase appears in one of the top 5 results. Labelling by phrase rather than chunk ID keeps the test set valid when the chunk size changes.

`eval.py` reports, per mode:
- **recall@5**: how often the right passage is in the top 5
- **MRR**: how high it ranks (1.0 = always first)
- **ms/query**: what each stage costs in latency

## Results

_To be filled in from real runs._
