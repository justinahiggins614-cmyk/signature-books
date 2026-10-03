#!/usr/bin/env python3
"""Integrity gates for The Signature Book Depository.
Fails (exit 1) if the catalog, manifest, index, chunks, or sitemap disagree.
Run after every drip and before every deploy:
    python3 code/qa_book_depository.py
"""
import gzip, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX = os.path.join(ROOT, "data", "index")
VOL = os.path.join(ROOT, "data", "volumes")
fails = []

def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ((" — " + detail) if detail and not cond else ""))
    if not cond:
        fails.append(name)

# --- load authoritative files ---
api = json.load(open(os.path.join(IDX, "api.json")))
with gzip.open(os.path.join(IDX, "books.idx.json.gz"), "rt", encoding="utf-8") as f:
    entries = json.load(f)
man = json.load(open(os.path.join(IDX, "books-manifest.json")))
cman = json.load(open(os.path.join(IDX, "chunks-manifest.json")))
schema = json.load(open(os.path.join(IDX, "books-schema.json")))

total = api["total_books"]
check("api.json has required fields",
      all(k in api for k in ("total_books", "total_words", "genres", "origins",
                             "chunks", "march_goal", "updated", "schema", "manifest")),
      "missing keys")
check("index entry count == api.total_books", len(entries) == total,
      f"index={len(entries)} api={total}")
check("genre counts sum == total_books",
      sum(api["genres"].values()) == total,
      f"sum={sum(api['genres'].values())}")
check("origin counts sum == total_books (mutually exclusive, cumulative)",
      sum(api["origins"].values()) == total,
      f"sum={sum(api['origins'].values())} origins={api['origins']}")
check("manifest counts match api", man["total_books"] == total
      and man["total_words"] == api["total_words"]
      and man["origin_counts"] == api["origins"],
      "books-manifest.json drifted from api.json")
check("chunk manifest total == total_books",
      cman["total_books"] == total and cman["chunk_count"] == api["chunks"],
      f"cman={cman['total_books']}")

# --- ID integrity ---
ids = [e["id"] for e in entries]
check("no duplicate book IDs", len(set(ids)) == len(ids),
      f"{len(ids) - len(set(ids))} dupes")
want = [f"JAH-BOOK-{i:06d}" for i in range(1, total + 1)]
check("IDs contiguous 000001..%06d" % total, ids == want,
      "gap or misorder detected")
check("index entries carry required short fields",
      all(all(k in e for k in ("id", "t", "a", "g", "w", "d", "o", "ch")) for e in entries),
      "a row is missing fields")

# --- chunk files ---
missing = [n for n in range(1, api["chunks"] + 1)
           if not os.path.exists(os.path.join(VOL, f"books-c{n:05d}.json.gz"))]
check("all chunk files present", not missing, f"missing: {missing[:5]}")

# --- sitemap ---
sm = open(os.path.join(ROOT, "sitemap.xml")).read()
book_urls = len(re.findall(r"\?book=JAH-BOOK-", sm))
check("sitemap lists every book deep link", book_urls >= total,
      f"sitemap book urls={book_urls} total={total}")

# --- honesty: no fake ISBNs / publishers in sample records ---
sample = entries[::2059]  # ~10 spread across the catalog
bad = []
for e in sample:
    n = (int(e["id"][-6:]) - 1) // 100 + 1
    with gzip.open(os.path.join(VOL, f"books-c{n:05d}.json.gz"), "rt", encoding="utf-8") as f:
        recs = json.load(f)
    rec = next(r for r in recs if r["id"] == e["id"])
    blob = json.dumps(rec)
    if re.search(r"\bISBN\b", blob, re.I):
        bad.append(e["id"] + ":ISBN")
check("no fake ISBNs in sampled records", not bad, str(bad[:3]))

# --- schema sanity ---
check("books-schema.json parses with required record fields",
      all(k in schema["properties"] for k in ("id", "title", "chapters", "origin", "sources")),
      "schema incomplete")

print()
if fails:
    print(f"{len(fails)} GATE(S) FAILED: {fails}")
    sys.exit(1)
print("ALL BOOK DEPOSITORY GATES PASSED")
