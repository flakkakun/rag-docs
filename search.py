"""Retrieve the chunks that best answer a question.

    python search.py "how does HNSW work"
    python search.py "how does HNSW work" --mode vector

Modes, each one building on the last:
    vector   embedding similarity through the HNSW index
    keyword  Postgres full-text search (exact words)
    hybrid   both lists merged with reciprocal rank fusion
    rerank   hybrid, then a cross-encoder re-sorts the top candidates (default)
"""
import argparse

from common import connect, embed_query, reranker

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


def keyword_search(conn, question, k=CANDIDATES):
    # plainto_tsquery ANDs every word, so a full question rarely matches any
    # chunk. Swapping & for | means "any of these words", and ts_rank_cd then
    # scores chunks higher when they contain more of them, closer together.
    # This is BM25-like, not true BM25 (Postgres doesn't ship BM25).
    return conn.execute(
        """
        with q as (select replace(plainto_tsquery('english', %s)::text, '&', '|')::tsquery as q)
        select id, source, content from chunks, q
        where tsv @@ q.q
        order by ts_rank_cd(tsv, q.q) desc
        limit %s
        """,
        (question, k),
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


def search(conn, question, mode="rerank", k=5):
    if mode == "vector":
        results = vector_search(conn, question)
    elif mode == "keyword":
        results = keyword_search(conn, question)
    else:
        results = rrf(vector_search(conn, question), keyword_search(conn, question))
        if mode == "rerank":
            results = rerank(question, results)
    return results[:k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--mode", default="rerank", choices=["vector", "keyword", "hybrid", "rerank"])
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()

    with connect() as conn:
        for i, (_, source, content) in enumerate(search(conn, args.question, args.mode, args.k), 1):
            preview = " ".join(content.split())[:200]
            print(f"[{i}] {source}\n    {preview}...\n")


if __name__ == "__main__":
    main()
