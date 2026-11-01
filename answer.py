"""Answer a question from the documents, with numbered citations.

    python answer.py "Why is decoding memory-bound?"
    python answer.py "..." --mode hybrid -k 6
"""
import argparse
import re
import time
from difflib import SequenceMatcher

from common import LLM_MODEL, connect, llm
from search import search


def norm(s):
    # Lower-case, one space between words, and no quote marks: the model may
    # straighten curly quotes or drop the ones around a phrase it copies.
    return " ".join(re.sub(r"[\"“”'‘’]", "", s.lower()).split())


def quote_in(quote, source, min_share=0.9):
    """True if at least 90% of the quote appears word for word, in one piece, in
    the source. Allows a small slip like an added "And" at the start, but not a
    quote stitched together from different places."""
    q, s = norm(quote), norm(source)
    if not q:
        return False
    match = SequenceMatcher(None, q, s, autojunk=False).find_longest_match(0, len(q), 0, len(s))
    return match.size >= min_share * len(q)

REFUSAL = "I don't know based on the provided documents."

SYSTEM = f"""You answer questions using ONLY the numbered sources provided.

Rules:
- End every sentence with the number of the source its facts came from, like [1] or [2][3]. Check the number: it is the one in that source's <source id="..."> tag.
- Use only facts stated in the sources. Do not add anything from your own knowledge.
- Sources may use different words than the question: synonyms, spelled-out numbers, or the full name of a setting or abbreviation. If a source answers the question in other words, answer it.
- Check that the source is about the exact thing asked (the same GPU, model, setting, file or run). If the sources only cover a different one, do not answer with it.
- If the sources do not contain the answer, reply with exactly: {REFUSAL}

Otherwise reply in exactly this format:
QUOTE [n]: "the sentence from source n that answers the question, copied word for word"
ANSWER: your answer in 1 to 3 sentences, each ending with its source number.

Find the quote first, then write the answer from it. If no sentence in the sources answers the question, refuse instead."""

QUOTE = re.compile(r'QUOTE\s*\[(\d+)\]\s*:\s*"(.+?)"', re.S)


def build_prompt(question, chunks):
    # Numbered sources let the model cite by number, and let us check each
    # citation against the chunk it points to. Opening and closing tags make it
    # unambiguous which text belongs to which number; with only a "[2]" header
    # line, a small model sometimes credits text to the next source's number.
    sources = "\n\n".join(f'<source id="{i}" file="{source}">\n{content}\n</source>'
                          for i, (_, source, content) in enumerate(chunks, 1))
    # The question goes before the sources as well as after: read only at the
    # end of ~5,000 characters, a 7B model sometimes refused without looking.
    return f"Question: {question}\n\n{sources}\n\nQuestion: {question}"


def answer(conn, question, mode="rerank", k=4):
    chunks = search(conn, question, mode, k)
    start = time.perf_counter()
    reply = llm().chat.completions.create(
        model=LLM_MODEL,
        temperature=0,   # same question, same answer: needed for a repeatable eval
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": build_prompt(question, chunks)}],
    ).choices[0].message.content.strip()
    # The quote is checkable with a plain string match: is it really in the
    # source it names? That catches made-up support without a judge model.
    quotes = [(int(n), q.strip()) for n, q in QUOTE.findall(reply)]
    # The model often copies a real sentence but gives it the wrong source
    # number. So don't trust its number: find which source the quote is in.
    located = [next((i for i, c in enumerate(chunks, 1) if quote_in(q, c[2])), None) for _, q in quotes]
    found = [i is not None for i in located]
    text = reply.split("ANSWER:", 1)[1].strip() if "ANSWER:" in reply else reply
    refused = REFUSAL.lower().rstrip(".") in reply.lower()
    # Guardrail: an answer whose only support is a quote that is in none of the
    # sources is treated as made up, and replaced with the refusal.
    blocked = not refused and bool(quotes) and not any(found)
    if blocked:
        text, refused = REFUSAL, True
    # Correct the numbers in the answer to the sources the quotes were found in.
    fix = {n: i for (n, _), i in zip(quotes, located) if i is not None and i != n}
    text = re.sub(r"\[(\d+)\]", lambda m: f"[{fix.get(int(m.group(1)), int(m.group(1)))}]", text)
    corrected = bool(fix)
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", text)} | {i for i in located if i})
    return {
        "answer": text,
        "refused": refused,
        "blocked": blocked,                                # refused by the quote check, not the model
        "corrected": corrected,                            # the model's source number was wrong and fixed
        "chunks": chunks,
        "cited": cited,                                    # 1-based source numbers
        "invalid_citations": [n for n in cited if not 1 <= n <= len(chunks)],
        "quotes": quotes,
        "quotes_found": found,
        "llm_ms": (time.perf_counter() - start) * 1000,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--mode", default="rerank", choices=["vector", "keyword", "hybrid", "rerank"])
    ap.add_argument("-k", type=int, default=4, help="how many chunks to give the model")
    args = ap.parse_args()

    with connect() as conn:
        r = answer(conn, args.question, args.mode, args.k)
    for (n, q), found in zip(r["quotes"], r["quotes_found"]):
        print(f'quote [{n}] {"(found in the sources)" if found else "(NOT in any source)"}: "{q}"')
    if r["corrected"]:
        print("(the model's source number was wrong; corrected from where the quote was found)")
    print(r["answer"], "\n")
    for n in r["cited"]:
        if n not in r["invalid_citations"]:
            _, source, content = r["chunks"][n - 1]
            print(f"[{n}] {source}: {' '.join(content.split())[:160]}...")
    if r["invalid_citations"]:
        print(f"Warning: cited sources that don't exist: {r['invalid_citations']}")


if __name__ == "__main__":
    main()
