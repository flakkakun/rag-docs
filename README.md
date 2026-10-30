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
| **Chunking** | Packs whole paragraphs into ~1,200-character chunks, never across a section heading, repeating one paragraph between neighbours | Whole documents are too big to match precisely; one topic per chunk keeps its vector focused; overlap keeps ideas that cross a boundary intact |
| **Embedding** | `bge-small-en-v1.5` turns each chunk into 384 numbers | Similar meaning → nearby vectors |
| **Vector search** | pgvector **HNSW** index, `ef_search` = 100 | Finds near neighbours without scanning every vector; approximate, so `ef_search` trades recall for speed |
| **Keyword search** | **BM25** in SQL: Postgres full-text (GIN index) finds candidates, a word-frequency table supplies IDF | Embeddings are weak on exact terms: names, codes, numbers |
| **RRF** | Merges both lists by rank: `score = Σ 1/(60 + rank)` | The two searches score on different scales; ranks don't care |
| **Rerank** | `ms-marco-MiniLM-L-6` cross-encoder reads question + chunk together | More accurate than comparing vectors, too slow to run on everything |

Everything runs locally: Postgres + pgvector in Docker, models on CPU/Apple Silicon. No API keys.

## Run it

```bash
docker compose up -d                       # Postgres + pgvector on port 5433
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -r requirements.txt

python ingest.py                           # chunk, embed, store
python search.py "your question"           # --mode vector|keyword|hybrid|rerank
python eval.py                             # recall@5 for each mode (-k 1 for recall@1)
```

`data/` ships with the corpus used for the results below. To search your own documents, replace it with any `.md` / `.txt` files and write questions for them in `eval/questions.jsonl`.

## Evaluation

`eval/questions.jsonl` holds test questions, each with a short phrase that the right passage contains. A hit means that phrase appears in one of the top k results. Labelling by phrase rather than chunk ID keeps the test set valid when the chunk size changes. When the documents answer a question in more than one place, the question lists a phrase for each.

`eval.py` reports, per mode:
- **recall@k**: how often the right passage is in the top k, overall and per question type
- **MRR**: how high it ranks (1.0 = always first)
- **ms/query**: what each stage costs in latency

## Results

**Corpus** (in `data/`): a 10-chapter script explaining how LLM serving works (tokens, KV cache, batching, PagedAttention, TTFT/ITL/throughput, cost levers) plus the README of my [llm-serving](https://github.com/flakkakun/llm-serving) benchmark project. 11 files, 67 chunks. Many chapters cover overlapping topics, so the right passage has close competitors.

**Questions** (in `eval/questions.jsonl`): 52, hand-written, in three types:
- **paraphrase** (27): asked in different words from the source
- **exact** (11): names, numbers and identifiers ("H100", "`vllm:inter_token_latency_seconds`", "us-east")
- **needle** (14): one specific number in a topic several chunks cover ("How full was the KV cache at 64 users?")

| Mode | recall@5 | exact | needle | paraphrase | recall@1 | MRR | ms/query |
|---|---|---|---|---|---|---|---|
| vector | 87% | 82% | 93% | 85% | 48% | 0.63 | 10 |
| keyword (BM25) | 94% | 91% | 100% | 93% | 73% | 0.82 | 5 |
| hybrid (RRF) | **96%** | **100%** | 100% | 93% | 69% | 0.79 | 21 |
| hybrid + rerank | 92% | 82% | 100% | 93% | **83%** | **0.86** | 235 |

Measured on an M4 Mac (16 GB), local Postgres in Docker.

**What it shows:**
- **Vector search alone ranks the right passage first less than half the time** (48%). It finds the right area but not the right paragraph, and it misses identifiers like "H100".
- **BM25 is strong on this corpus.** Technical writing repeats exact terms (KV cache, TTFT, A10), which is what keyword search is built for.
- **Hybrid finds the most** (96% in the top 5). The two searches fail on different questions, so merging them covers both.
- **Reranking puts the right passage first far more often** (69% → 83% recall@1), but costs ~215 ms per query and **drops two exact-term questions** out of the top 5. The cross-encoder was trained on web search text and doesn't know that "H100" or a Prometheus metric name matters. Worth it when only the top 1–3 chunks go into the LLM prompt; not worth it when you pass 5+.

**Misses that remain:** "Should I always rent the biggest GPU?" (no mode finds the passage that says *not always "buy the biggest one"*; the question says "rent", the source says "buy") and "Why did the metrics dashboard stop showing data under heavy load?" (the reranker prefers a chapter about the dashboard over the README line about scrape timeouts).

## Lessons from building it

The pipeline was first developed against a private set of notes; these are the changes that made the biggest difference there, each measured one at a time.

1. **Check misses before blaming the model.** Twice, a "miss" was the reranker finding a *different* passage that also answered the question. The fix was in the test set (several valid phrases per question), not the search.
2. **A small, easy test set can't compare methods.** With 12 questions, every mode scored 100%. Harder question types and distractor documents made the differences visible.
3. **Postgres `ts_rank` is not BM25.** It has no IDF, so a word in every chunk counts as much as a word in one. Computing BM25 in SQL with a document-frequency table raised keyword recall noticeably.
4. **Chunks should not cross section headings.** A chunk holding the end of one topic and the start of another gets a vector that matches neither well. Respecting headings gave the biggest single gain.
