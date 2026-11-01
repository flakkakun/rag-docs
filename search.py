"""Retrieve the chunks that best answer a question.

    python search.py "how does HNSW work"
    python search.py "how does HNSW work" --mode vector

Modes, each one building on the last:
    vector   embedding similarity through the HNSW index
    keyword  Postgres full-text search (exact words)
    hybrid   both lists merged with reciprocal rank fusion
    rerank   hybrid, then a cross-encoder re-sorts the top candidates (default)
    rewrite  an LLM rewrites the question too; both are searched, then rerank
"""
import argparse
from functools import cache

from common import REWRITE_MODEL, connect, embed_query, llm, reranker

CANDIDATES = 50   # how many each first-stage search returns
RERANK_TOP = 30   # how many the cross-encoder reads (it's the slow step)


def vector_search(conn, question, k=CANDIDATES, ef_search=100):
    # ef_search = size of the candidate shortlist in HNSW's bottom layer.
    # Must be >= k, otherwise you can't get k results back.
    conn.execute(f"set hnsw.ef_search = {max(ef_search, k)}")
    return conn.execute(
        "select id, source, content from chunks order by embedding <=> %s limit %s",
        (embed_query(question), k),
    ).fetchall()


def keyword_search(conn, question, k=CANDIDATES, k1=1.2, b=0.75):
    """BM25, computed in SQL. Postgres's own ts_rank has no IDF, so a common
    word like "use" counts as much as a rare one like "Orca".

    For each query word found in a chunk:
        idf  = ln(1 + (N - df + 0.5) / (df + 0.5))       rare words score higher
        tf'  = tf * (k1 + 1) / (tf + k1 * (1 - b + b * len / avg_len))
    and the chunk's score is the sum of idf * tf'. k1 caps how much repeating a
    word helps; b stops long chunks winning just by containing more words.
    """
    # plainto_tsquery ANDs every word, so a full question rarely matches any
    # chunk. Swapping & for | means "any of these words"; the GIN index uses it
    # to find candidate chunks before scoring.
    return conn.execute(
        """
        with q as (
          select distinct lexeme as term from unnest(to_tsvector('english', %(q)s))
        ), n as (
          select count(*)::float as n, avg(length(tsv))::float as avg_len from chunks
        )
        select c.id, c.source, c.content
        from chunks c
        cross join n
        cross join lateral unnest(c.tsv) t
        join q on q.term = t.lexeme
        join term_stats s on s.term = t.lexeme
        where c.tsv @@ replace(plainto_tsquery('english', %(q)s)::text, '&', '|')::tsquery
        group by c.id, c.source, c.content
        order by sum(
          ln(1 + (n.n - s.ndoc + 0.5) / (s.ndoc + 0.5))
          * cardinality(t.positions) * (%(k1)s + 1)
          / (cardinality(t.positions) + %(k1)s * (1 - %(b)s + %(b)s * length(c.tsv) / n.avg_len))
        ) desc
        limit %(k)s
        """,
        {"q": question, "k": k, "k1": k1, "b": b},
    ).fetchall()


def rrf(*ranked_lists, k=60):
    """Reciprocal rank fusion: score = sum of 1 / (k + rank) across lists.

    Uses only rank positions, so it doesn't matter that cosine distances and
    text-search scores are on completely different scales. k=60 is the value
    from the original paper; it stops the #1 spot from dominating everything.
    """
    scores, rows = {}, {}
    for results in ranked_lists:
        for rank, row in enumerate(results, start=1):
            scores[row[0]] = scores.get(row[0], 0) + 1 / (k + rank)
            rows[row[0]] = row
    return [rows[i] for i in sorted(scores, key=scores.get, reverse=True)]


def rerank(question, rows, top=RERANK_TOP):
    # A cross-encoder reads question and chunk together, so it sees how the
    # words relate. More accurate than comparing two separate vectors, but it
    # has to run once per chunk, which is why it only gets the top few.
    rows = rows[:top]
    if not rows:
        return rows
    scores = reranker().predict([(question, r[2]) for r in rows])
    return [r for _, r in sorted(zip(scores, rows), key=lambda p: p[0], reverse=True)]


REWRITE_PROMPT = """Rewrite the user's question as a search query for a collection of technical documents.
- Keep every exact name, number, code identifier and metric name unchanged.
- Add common synonyms or the more technical term for the key words.
- Reply with the query only, on one line."""


@cache   # same question, same rewrite (temperature 0), so don't pay for it twice
def rewrite_query(question):
    return llm().chat.completions.create(
        model=REWRITE_MODEL,
        temperature=0,
        messages=[{"role": "system", "content": REWRITE_PROMPT},
                  {"role": "user", "content": question}],
    ).choices[0].message.content.strip().strip('"')


def search(conn, question, mode="rerank", k=5):
    if mode == "vector":
        results = vector_search(conn, question)
    elif mode == "keyword":
        results = keyword_search(conn, question)
    elif mode == "rewrite":
        # Search with the original AND the rewrite: a rewrite can lose an exact
        # term the original had, so it adds candidates rather than replacing them.
        # The reranker still scores against the original, which is what was asked.
        rewritten = rewrite_query(question)
        results = rerank(question, rrf(vector_search(conn, question), keyword_search(conn, question),
                                       vector_search(conn, rewritten), keyword_search(conn, rewritten)))
    else:
        results = rrf(vector_search(conn, question), keyword_search(conn, question))
        if mode == "rerank":
            results = rerank(question, results)
    return results[:k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--mode", default="rerank", choices=["vector", "keyword", "hybrid", "rerank", "rewrite"])
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()

    if args.mode == "rewrite":
        print(f"rewritten: {rewrite_query(args.question)}\n")
    with connect() as conn:
        for i, (_, source, content) in enumerate(search(conn, args.question, args.mode, args.k), 1):
            preview = " ".join(content.split())[:200]
            print(f"[{i}] {source}\n    {preview}...\n")


if __name__ == "__main__":
    main()
