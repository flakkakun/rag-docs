"""Measure retrieval quality: does the right chunk come back in the top k?

    python eval.py               # compares all four search modes
    python eval.py -k 3

eval/questions.jsonl holds one test case per line:
    {"question": "...", "answer_contains": "a short phrase from the right passage", "type": "exact"}

`type` is optional. When present, recall is also broken down by type, which
shows *where* each mode is weak instead of hiding it in one average.

A hit means one of the top k chunks contains that phrase. Labelling by phrase
instead of chunk id means the test set survives re-chunking with a new size.
When the docs answer a question in more than one place, give a list:
    {"question": "...", "answer_contains": ["phrase from place A", "phrase from place B"]}
Otherwise a correct answer from place B gets scored as a miss.
"""
import argparse
import json
import time
from collections import defaultdict

from common import connect
from search import search

MODES = ["vector", "keyword", "hybrid", "rerank"]


def norm(s):
    return " ".join(s.lower().split())


def rank_of(results, case):
    targets = case["answer_contains"]
    targets = [norm(t) for t in ([targets] if isinstance(targets, str) else targets)]
    return next((i for i, r in enumerate(results, 1)
                 if any(t in norm(r[2]) for t in targets)), None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="eval/questions.jsonl")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--misses", action="store_true", help="list the questions each mode missed")
    args = ap.parse_args()

    with open(args.questions) as f:
        cases = [json.loads(line) for line in f if line.strip()]
    types = sorted({c.get("type", "all") for c in cases})
    per_type = {t: sum(c.get("type", "all") == t for c in cases) for t in types}

    print(f"{len(cases)} questions, k={args.k}  ({', '.join(f'{t}: {n}' for t, n in per_type.items())})\n")
    header = f"{'mode':<8}  {'recall@' + str(args.k):>9}" + "".join(f"  {t:>10}" for t in types)
    print(header + f"  {'MRR':>5}  {'ms/query':>8}")
    with connect() as conn:
        search(conn, "warm up", "rerank")   # load both models before timing
        for mode in MODES:
            hits, rr, misses = defaultdict(int), 0.0, []
            start = time.perf_counter()
            for case in cases:
                rank = rank_of(search(conn, case["question"], mode, args.k), case)
                if rank:
                    hits[case.get("type", "all")] += 1
                    rr += 1 / rank   # MRR: 1.0 if the right chunk is first, 0.5 if second...
                else:
                    misses.append(case["question"])
            ms = (time.perf_counter() - start) / len(cases) * 1000
            row = f"{mode:<8}  {sum(hits.values()) / len(cases):>9.0%}"
            row += "".join(f"  {hits[t] / per_type[t]:>10.0%}" for t in types)
            print(row + f"  {rr / len(cases):>5.2f}  {ms:>8.0f}")
            if args.misses:
                for q in misses:
                    print(f"            miss: {q}")


if __name__ == "__main__":
    main()
