"""Measure the generated answers, not just retrieval.

    python eval_answers.py               # all questions
    python eval_answers.py --limit 10    # quick check
    python eval_answers.py --show        # print every failure with its answer

Answerable questions (eval/questions.jsonl), for each one:
    retrieved   the right passage was among the chunks given to the model
    answered    the model answered instead of refusing
    cited       one of its citations points at a chunk holding the right passage

Splitting these apart says *which* stage failed: if the passage was retrieved
but not cited, the model is at fault; if it was never retrieved, search is.

Unanswerable questions (eval/unanswerable.jsonl): the model should refuse.
"off-topic" ones are clearly outside the documents; "trap" ones sound like
the documents answer them but don't (e.g. results for a run never done).

No LLM judge: every check is a string match, so the numbers are exact and
free to recompute. It doesn't check that every sentence is supported by the
source it cites; the quote check in answer.py covers the sentence the answer
rests on.
"""
import argparse
import json
from collections import defaultdict

from answer import answer
from common import LLM_MODEL, connect
from eval import norm


def targets(case):
    t = case["answer_contains"]
    return [norm(x) for x in ([t] if isinstance(t, str) else t)]


def holds_answer(chunk, case):
    return any(t in norm(chunk[2]) for t in targets(case))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="rerank")
    ap.add_argument("-k", type=int, default=4)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    answerable = [json.loads(l) for l in open("eval/questions.jsonl") if l.strip()][: args.limit]
    unanswerable = [json.loads(l) for l in open("eval/unanswerable.jsonl") if l.strip()][: args.limit]
    counts, failures, llm_ms = defaultdict(int), [], []

    with connect() as conn:
        for case in answerable:
            r = answer(conn, case["question"], args.mode, args.k)
            llm_ms.append(r["llm_ms"])
            retrieved = any(holds_answer(c, case) for c in r["chunks"])
            cited = any(holds_answer(r["chunks"][n - 1], case)
                        for n in r["cited"] if n not in r["invalid_citations"])
            counts["retrieved"] += retrieved
            counts["answered"] += not r["refused"]
            counts["cited"] += cited
            counts["invalid"] += bool(r["invalid_citations"])
            counts["blocked"] += r["blocked"]
            counts["corrected"] += r["corrected"]
            if retrieved and not cited:
                why = "refused although the passage was retrieved" if r["refused"] else "answered but didn't cite the right passage"
                failures.append((why, case["question"], r["answer"]))

        by_type = defaultdict(lambda: [0, 0])
        for case in unanswerable:
            r = answer(conn, case["question"], args.mode, args.k)
            llm_ms.append(r["llm_ms"])
            by_type[case["type"]][0] += r["refused"]
            by_type[case["type"]][1] += 1
            counts["blocked_unanswerable"] += r["blocked"]
            if not r["refused"]:
                failures.append(("answered an unanswerable question", case["question"], r["answer"]))

    n = len(answerable)
    print(f"model: {LLM_MODEL}   retrieval: {args.mode}, top {args.k} chunks\n")
    print(f"Answerable ({n})")
    print(f"  right passage retrieved   {counts['retrieved'] / n:>5.0%}")
    print(f"  answered (not refused)    {counts['answered'] / n:>5.0%}")
    print(f"  cited the right passage   {counts['cited'] / n:>5.0%}")
    print(f"  cited a source that doesn't exist  {counts['invalid']}")
    print(f"  blocked by the quote check  {counts['blocked']}")
    print(f"  source number corrected from the quote  {counts['corrected']}")
    print(f"\nUnanswerable ({len(unanswerable)})")
    for t, (refused, total) in sorted(by_type.items()):
        print(f"  refused, {t:<10} {refused}/{total}")
    print(f"  (of those, blocked by the quote check: {counts['blocked_unanswerable']})")
    print(f"\nLLM time per answer: mean {sum(llm_ms) / len(llm_ms) / 1000:.1f} s, "
          f"median {sorted(llm_ms)[len(llm_ms) // 2] / 1000:.1f} s")
    print(f"\n{len(failures)} failures" + ("" if args.show else " (--show to list)"))
    if args.show:
        for why, q, a in failures:
            print(f"\n- {why}\n  Q: {q}\n  A: {' '.join(a.split())[:300]}")


if __name__ == "__main__":
    main()
