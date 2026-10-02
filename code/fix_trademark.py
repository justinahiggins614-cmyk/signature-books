#!/usr/bin/env python3
"""One-time trademark-safety fix for the 3,000 seeded books.

Scans every book's title, desc, and chapter titles/bodies with
code/trademark_safe.py and replaces any trademarked term or thin knockoff
with an invented substitute.

Guarantees:
  - JAH-BOOK-###### IDs never change; chunk structure (100-book gz files)
    is preserved; only chunks containing a fix are rewritten.
  - Deterministic: book #i is fixed with G(SALT + i + FIX_SALT), so a
    re-run is a no-op (idempotent).
  - data/index/books.idx.json.gz entries (title/desc/chapter titles/words)
    are updated for fixed books; api.json word total is recounted.

Usage: python3 code/fix_trademark.py [--dry-run]
"""
import gzip, glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from trademark_safe import sanitize_book_text
from drip_books import G, SALT, words_of  # noqa

ROOT = os.path.dirname(HERE)
IDX_P = os.path.join(ROOT, "data", "index", "books.idx.json.gz")
API_P = os.path.join(ROOT, "data", "index", "api.json")
FIX_SALT = 770001

DRY = "--dry-run" in sys.argv


def fix_record(rec, idx):
    g = G(SALT + idx + FIX_SALT)
    changed = []
    t2, n = sanitize_book_text(rec["title"], g)
    if n:
        rec["title"] = t2
        changed.append(("title", n))
    d2, n = sanitize_book_text(rec["desc"], g)
    if n:
        rec["desc"] = d2
        changed.append(("desc", n))
    for c in rec["chapters"]:
        t3, n = sanitize_book_text(c["t"], g)
        if n:
            c["t"] = t3
            changed.append(("ch_title", n))
        b3, n = sanitize_book_text(c["b"], g)
        if n:
            c["b"] = b3
            changed.append(("ch_body", n))
    if changed:
        rec["words"] = (sum(words_of(c["b"]) + words_of(c["t"])
                            for c in rec["chapters"])
                        + words_of(rec["title"]) + words_of(rec["desc"]))
    return changed


def main():
    chunk_files = sorted(glob.glob(os.path.join(ROOT, "data", "volumes",
                                                "*.gz")))
    books, order = {}, []
    for f in chunk_files:
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            recs = json.load(fh)
        for r in recs:
            books[r["id"]] = (f, r)
            order.append(r["id"])

    total_changed, total_repl = 0, 0
    changed_chunks = set()
    per_book = {}
    for bid in order:
        idx = int(bid.rsplit("-", 1)[1])
        f, rec = books[bid]
        ch = fix_record(rec, idx)
        if ch:
            total_changed += 1
            total_repl += sum(n for _, n in ch)
            changed_chunks.add(f)
            per_book[bid] = ch

    # title uniqueness across the whole set after fixes
    if not DRY:
        seen = {}
        for bid in order:
            rec = books[bid][1]
            t = rec["title"]
            if t in seen:
                rec["title"] = f"{t} (Signature Edition)"
                per_book.setdefault(bid, []).append(("dedup", 1))
                changed_chunks.add(books[bid][0])
            seen[rec["title"]] = bid

    print(f"books fixed: {total_changed}/{len(order)}  "
          f"replacements: {total_repl}  chunks touched: {len(changed_chunks)}")
    for bid, ch in sorted(per_book.items())[:60]:
        print(" ", bid, ch)
    if len(per_book) > 60:
        print(f"  ... and {len(per_book) - 60} more")

    if DRY:
        print("dry run: nothing written")
        return

    # rewrite touched chunks (same 100-book structure, same IDs/order)
    by_chunk = {}
    for bid in order:
        f, rec = books[bid]
        by_chunk.setdefault(f, []).append(rec)
    for f in changed_chunks:
        with gzip.open(f, "wt", encoding="utf-8") as fh:
            json.dump(by_chunk[f], fh, ensure_ascii=False,
                      separators=(",", ":"))
    print(f"rewrote {len(changed_chunks)} chunk files")

    # refresh search-index entries for fixed books
    with gzip.open(IDX_P, "rt", encoding="utf-8") as fh:
        entries = json.load(fh)
    by_id = {r["id"]: r for f in chunk_files for r in
             json.load(gzip.open(f, "rt", encoding="utf-8"))}
    for e in entries:
        r = by_id.get(e["id"])
        if r is None:
            continue
        e["t"] = r["title"]
        e["d"] = r["desc"]
        e["w"] = r["words"]
        e["ch"] = [c["t"] for c in r["chapters"]]
    with gzip.open(IDX_P, "wt", encoding="utf-8") as fh:
        json.dump(entries, fh, ensure_ascii=False, separators=(",", ":"))
    print("index refreshed")

    # recount words in api.json
    total_words = sum(e["w"] for e in entries)
    with open(API_P, encoding="utf-8") as fh:
        api = json.load(fh)
    api["total_words"] = total_words
    api["note"] = (api.get("note", "") +
                   " Trademark-safety pass 2026-10-02: all titles and text "
                   "screened; any trademarked term or knockoff replaced with "
                   "invented names.")
    with open(API_P, "w", encoding="utf-8") as fh:
        json.dump(api, fh, ensure_ascii=False, indent=1)
    print("api.json words:", total_words)

    # verify: rescan everything, expect zero hits
    bad = 0
    for bid in order:
        r = books[bid][1]
        blob = r["title"] + "\n" + r["desc"] + "\n" + "\n".join(
            c["t"] + "\n" + c["b"] for c in r["chapters"])
        import random as _r
        g2 = G(SALT + idx + FIX_SALT)
        if sanitize_book_text(blob, g2)[1]:
            bad += 1
            print("STILL BAD:", bid)
    print("post-fix residual violations:", bad)


if __name__ == "__main__":
    main()
