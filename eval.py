"""Measure retrieval quality: does the right chunk come back in the top k?

    python eval.py               # compares all four search modes
    python eval.py -k 3

eval/questions.jsonl holds one test case per line:
    {"question": "...", "answer_contains": "a short phrase from the right passage"}

A hit means one of the top k chunks contains that phrase. Labelling by phrase
instead of chunk id means the test set survives re-chunking with a new size.
When the docs answer a question in more than one place, give a list:
    {"question": "...", "answer_contains": ["phrase from place A", "phrase from place B"]}
Otherwise a correct answer from place B gets scored as a miss.
"""
import argparse
import json
import re
import time

from common import connect
from search import search

MODES = ["vector", "keyword", "hybrid", "rerank"]


def norm(s):
    return " ".join(s.lower().split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="eval/questions.jsonl")
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()

    with open(args.questions) as f:
        cases = [json.loads(line) for line in f if line.strip()]

    print(f"{len(cases)} questions, k={args.k}\n")
    print(f"{'mode':<8}  {'recall@' + str(args.k):>9}  {'MRR':>5}  {'ms/query':>8}")
    with connect() as conn:
        search(conn, "warm up", "rerank")   # load both models before timing
        for mode in MODES:
            hits, rr, misses = 0, 0.0, []
            start = time.perf_counter()
            for case in cases:
                results = search(conn, case["question"], mode, args.k)
                targets = case["answer_contains"]
                targets = [norm(t) for t in ([targets] if isinstance(targets, str) else targets)]
                rank = next((i for i, r in enumerate(results, 1)
                             if any(t in norm(r[2]) for t in targets)), None)
                if rank:
                    hits += 1
                    rr += 1 / rank   # MRR: 1.0 if the right chunk is first, 0.5 if second...
                else:
                    misses.append(case["question"])
            ms = (time.perf_counter() - start) / len(cases) * 1000
            print(f"{mode:<8}  {hits / len(cases):>9.0%}  {rr / len(cases):>5.2f}  {ms:>8.0f}")
            for q in misses:
                print(f"            miss: {q}")


if __name__ == "__main__":
    main()
