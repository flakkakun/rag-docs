"""Read every .md/.txt file in data/, chunk it, embed it, store it in Postgres.

    python ingest.py            # re-ingests everything from scratch
    python ingest.py --size 800 # try a different chunk size
"""
import argparse
import re
from pathlib import Path

from common import connect, embed_docs


# A line that starts a new section: a markdown heading ("## Costs") or a
# numbered one ("3.2 Results").
SECTION_START = re.compile(r"^(#{1,6} |\d+(\.\d+)+\s*\S)")


def chunk(text, size=1200, overlap=1):
    """Pack whole paragraphs into chunks of up to `size` characters, never
    letting a chunk run across a section boundary.

    Splitting on paragraphs (blank lines) keeps sentences intact, unlike a fixed
    character window. Starting fresh at each section keeps one topic per chunk,
    so its vector isn't an average of two unrelated topics. Within a long
    section, the last `overlap` paragraph(s) of each chunk are repeated at the
    start of the next, so an idea that spans a boundary is still whole in at
    least one chunk.
    """
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current = [], []
    for p in paras:
        new_section = SECTION_START.match(p)
        if current and (new_section or len("\n\n".join(current + [p])) > size):
            chunks.append("\n\n".join(current))
            current = [] if new_section or not overlap else current[-overlap:]
        current.append(p)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--size", type=int, default=1200)
    args = ap.parse_args()

    rows = []
    for path in sorted(Path(args.data).rglob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        for i, c in enumerate(chunk(path.read_text(errors="ignore"), args.size)):
            rows.append((path.name, i, c))
    if not rows:
        raise SystemExit(f"No .md/.txt files in {args.data}/")

    print(f"Embedding {len(rows)} chunks...")
    vectors = embed_docs([r[2] for r in rows])

    with connect() as conn:
        conn.execute("truncate chunks restart identity")
        with conn.cursor() as cur:
            cur.executemany(
                "insert into chunks (source, position, content, embedding) values (%s, %s, %s, %s)",
                [(s, i, c, v) for (s, i, c), v in zip(rows, vectors)],
            )
        # Document frequencies for BM25. Computed once here, like a search
        # engine does at index time, rather than on every query.
        conn.execute("truncate term_stats")
        conn.execute("insert into term_stats select word, ndoc from ts_stat('select tsv from chunks')")
    print(f"Stored {len(rows)} chunks from {len({r[0] for r in rows})} files.")


if __name__ == "__main__":
    main()
