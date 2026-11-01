# RAG over Documents: Hybrid Search, Reranking and Cited Answers, Measured

Answers questions from a folder of documents with a local LLM, citing the passage each answer comes from, and measures every stage: how often search finds the right passage, how often the answer cites it, and whether the model refuses questions the documents can't answer.

## How it works

```
                 ┌─▶ vector search (HNSW index, top 50) ──┐
question ──embed─┤                                         ├─▶ RRF merge ─▶ cross-encoder rerank (top 30) ─▶ top 4
                 └─▶ keyword search (full-text, top 50) ──┘                                                     │
                                                                                                                ▼
                    answer with [n] citations  ◀── quote check ◀── LLM (quote, then answer) ◀── numbered sources
                    or "I don't know based on the provided documents."
```

| Stage | What it does | Why |
|---|---|---|
| **Chunking** | Packs whole paragraphs into ~1,200-character chunks, never across a section heading, repeating one paragraph between neighbours | Whole documents are too big to match precisely; one topic per chunk keeps its vector focused; overlap keeps ideas that cross a boundary intact |
| **Embedding** | `bge-small-en-v1.5` turns each chunk into 384 numbers | Similar meaning → nearby vectors |
| **Vector search** | pgvector **HNSW** index, `ef_search` = 100 | Finds near neighbours without scanning every vector; approximate, so `ef_search` trades recall for speed |
| **Keyword search** | **BM25** in SQL: Postgres full-text (GIN index) finds candidates, a word-frequency table supplies IDF | Embeddings are weak on exact terms: names, codes, numbers |
| **RRF** | Merges both lists by rank: `score = Σ 1/(60 + rank)` | The two searches score on different scales; ranks don't care |
| **Rerank** | `ms-marco-MiniLM-L-6` cross-encoder reads question + chunk together | More accurate than comparing vectors, too slow to run on everything |
| **Generate** | Qwen 2.5 7B (via Ollama) gets the top 4 chunks as numbered sources, copies the sentence it relies on, then answers with `[n]` citations or refuses | The quote makes the answer checkable |
| **Quote check** | Finds the quote in the sources with a string match; fixes the citation number if the model got it wrong; blocks the answer if the quote is in no source | Catches made-up support without a judge model |

Everything runs locally: Postgres + pgvector in Docker, models on CPU/Apple Silicon, the LLM in Ollama. No API keys. The LLM client is OpenAI-compatible, so `LLM_BASE_URL` can point at a vLLM server instead.

## Run it

```bash
docker compose up -d                       # Postgres + pgvector on port 5433
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -r requirements.txt

python ingest.py                           # chunk, embed, store
python search.py "your question"           # --mode vector|keyword|hybrid|rerank
python eval.py                             # recall@5 for each mode (-k 1 for recall@1)

ollama pull qwen2.5:7b-instruct            # the answering model (Ollama running locally)
python answer.py "your question"           # answer + quote + cited sources
python eval_answers.py --show              # answer quality on all questions (~10 min)
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

**Misses that remain:** "Should I always rent the biggest GPU?" (the question says "rent", the source says "buy") and "Why did the metrics dashboard stop showing data under heavy load?" (the reranker prefers a chapter about the dashboard over the README line about scrape timeouts). Tracing all four rerank misses showed the same thing: the right chunk was already in the candidates, at rank 5 or 6, and the **reranker pushed it down** to rank 7–11.

### Query rewriting didn't help, and why

`--mode rewrite` has the LLM rewrite the question, searches with both the original and the rewrite, merges all four lists with RRF, then reranks against the original.

| Mode | recall@5 | MRR | ms/query |
|---|---|---|---|
| hybrid + rerank | 92% | 0.86 | 246 |
| + query rewrite (Qwen 2.5 7B) | 92% | 0.86 | 1,467 |

Same four misses, six times slower. Rewriting helps search *find* candidates, but here the right chunks were already found; the loss happens at the reranker, a later stage. The 7B rewrites were also mostly word swaps ("rent" → "lease"). Query rewriting is kept as an option, off by default. The next thing to try is the reranker itself.

## Answer generation

`eval_answers.py` runs every question through the full pipeline and checks the answer, separately for each stage, so a failure points at the stage that caused it:
- **right passage retrieved**: the passage was among the 4 chunks given to the model (if not, search failed)
- **cited the right passage**: one of the answer's citations points at a chunk holding it (if it was retrieved but not cited, the model failed)
- **refusals**: 10 extra questions in `eval/unanswerable.jsonl` the documents can't answer. 5 are **off-topic** (LoRA, GPT-4's context window). 5 are **traps** that sound answerable but aren't, like "What was the measured TTFT on the L4?" when the only benchmark ran on an A10.

Every check is a string match, so the numbers are exact and cost nothing to recompute.

**Results** (Qwen 2.5 7B in Ollama, temperature 0, top 4 reranked chunks):

| | first prompt | final prompt |
|---|---|---|
| right passage retrieved | 92% | 92% |
| answered (not refused) | 92% | 92% |
| cited the right passage | 79% | **85%** |
| cited a source that doesn't exist | 0 | 0 |
| refused off-topic questions | 5/5 | 5/5 |
| refused trap questions | 4/5 | **5/5** |
| LLM time per answer (mean) | 9.6 s | 10.3 s |

Search finds the right passage for 48 of 52 questions; the final prompt cites it in 44 of those 48.

**What changed, and what each fix was for:**
1. **The question goes before the sources as well as after.** Asked only after ~5,000 characters of sources, the 7B model sometimes refused at a glance, even when source [1] stated the answer.
2. **Quote first, then answer.** The model copies the sentence it relies on (`QUOTE [n]: "..."`) before answering.
3. **Check the quote with a string match.** This exposed the biggest problem: the model often copies a real sentence but **labels it with the wrong source number**. That happened in 7 of the 52 answers, and the first eval only noticed it when it hit the right passage. The code now finds the quote in the sources itself and corrects the number. A quote that is in no source means the support was made up, so the answer is replaced with the refusal. That caught the one trap the model answered: L4 numbers taken from the A10 results table.

**Limits of these numbers:**
- **They are a bit optimistic.** The prompt was changed while looking at failures from this same question set. A fresh set of questions would be the honest test.
- **Runs aren't perfectly repeatable.** Even at temperature 0, one question ("Which Modal region did the client call?") was answered in one run and refused in another.
- **The quote check isn't perfect.** It wrongly blocks 2 good answers where the model reworded its quote slightly.
- **It only checks the quoted sentence.** It doesn't check that every sentence of the answer is supported; that needs a judge model.

**Failures left (4):** three refusals where the passage was retrieved (two of them wrongly blocked by the quote check), and one answer that cited the wrong passage.

## Lessons from building it

The pipeline was first developed against a private set of notes; these are the changes that made the biggest difference there, each measured one at a time.

1. **Check misses before blaming the model.** Twice, a "miss" was the reranker finding a *different* passage that also answered the question. The fix was in the test set (several valid phrases per question), not the search.
2. **A small, easy test set can't compare methods.** With 12 questions, every mode scored 100%. Harder question types and distractor documents made the differences visible.
3. **Postgres `ts_rank` is not BM25.** It has no IDF, so a word in every chunk counts as much as a word in one. Computing BM25 in SQL with a document-frequency table raised keyword recall noticeably.
4. **Chunks should not cross section headings.** A chunk holding the end of one topic and the start of another gets a vector that matches neither well. Respecting headings gave the biggest single gain.
5. **Find which stage fails before adding a technique.** Query rewriting is a standard fix for paraphrase misses, but tracing the misses showed search had already found the right chunks. The reranker was dropping them, so rewriting couldn't help.
6. **Don't trust a small model's citation numbers.** Making it quote its source showed it often had the right sentence under the wrong number. Checking the quote with a string match fixed more answers than any prompt wording.
