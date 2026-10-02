"""Six-source pools for derived books (the progress loop).

Each drip run rebuilds pools from the CURRENT state of the six network
sources, so new specs / wiki articles / dossiers / patents / AIs / mall
products automatically become eligible as book seeds. A book's source pick
is hash-stable within its run: pool[sha1(kind:book_idx) % len(pool)].
Books are never regenerated, so existing books never change.

Pool entry: (sid, title, blurb, url). A missing/unreadable source yields
an empty pool; the generator then falls back to a standalone book.
"""
import gzip
import hashlib
import json
import os
import re

WS = os.path.expanduser("~/workspace")
POOL_CAP = 20000

SPEC_URL = "https://justinahiggins614-cmyk.github.io/signature-one-archive/specs.html?spec="
WIKI_URL = "https://justinahiggins614-cmyk.github.io/jah-wiki/"
LEAKS_URL = "https://justinahiggins614-cmyk.github.io/jah-n-wiki-leaks/?dossier="
PATENT_URL = "https://justinahiggins614-cmyk.github.io/cyber-patent-catalog/?patent="
AI_URL = "https://justinahiggins614-cmyk.github.io/jah-ai-models/#"
MALL_URL = "https://justinahiggins614-cmyk.github.io/signature-cyber-mega-mall/?product="


def _cap(pool):
    if len(pool) <= POOL_CAP:
        return pool
    step = len(pool) / POOL_CAP
    return [pool[int(i * step)] for i in range(POOL_CAP)]


def _spec_titles_all():
    """Single streaming pass: extract every (id, title) in the main index."""
    p = os.path.join(WS, "signature-one-archive/data/index/specs.idx.json.gz")
    out = []
    if not os.path.exists(p):
        return out
    pat = re.compile(rb'\["(JAH-SPEC-\d+)",\s*"((?:[^"\\]|\\.)*)"')

    def _emit(scan):
        for m in pat.finditer(scan):
            sid = m.group(1).decode()
            try:
                title = json.loads('"' + m.group(2).decode() + '"')
            except Exception:
                title = m.group(2).decode(errors="replace")
            out.append((sid, title))

    try:
        with gzip.open(p, "rb") as f:
            buf = b""
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    _emit(buf)
                    break
                buf += chunk
                # scan all but a tail that may hold a split match
                _emit(buf[:-2048])
                buf = buf[-2048:]
    except Exception:
        pass
    seen, uniq = set(), []
    for sid, title in out:
        if sid not in seen:
            seen.add(sid)
            uniq.append((sid, title))
    return uniq


def _spec_pool():
    pairs = _cap(_spec_titles_all())
    return [(sid, title, "", SPEC_URL + sid) for sid, title in pairs]


def _patent_pool():
    p = os.path.join(WS, "cyber-patent-catalog/data/patents.idx.json.gz")
    try:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            entries = json.load(f)
    except Exception:
        return []
    pool = []
    for e in entries:
        try:
            pubno, title = e[0], e[1]
        except Exception:
            continue
        pool.append((str(pubno), str(title), "", PATENT_URL + str(pubno)))
    return _cap(pool)


def _wiki_pool(spec_pool, patent_pool):
    pool = []
    for sid, title, _b, _u in _cap(list(spec_pool)):
        pool.append((sid, title, "", WIKI_URL + "?spec=" + sid))
    for pubno, title, _b, _u in _cap(list(patent_pool)):
        pool.append((pubno, title, "", WIKI_URL + "?patent=" + pubno))
    return _cap(pool)


def _leaks_pool():
    p = os.path.join(WS, "jah-n-wiki-leaks/data/bizarre/bizarre.idx.json.gz")
    pool = []
    try:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("["):
                    continue
                try:
                    e = json.loads(line)
                    did, title = e[0], e[1]
                    cat = e[2] if len(e) > 2 else ""
                except Exception:
                    continue
                pool.append((str(did), str(title), str(cat), LEAKS_URL + str(did)))
    except Exception:
        return []
    return _cap(pool)


def _ai_pool():
    p = os.path.join(WS, "jah-ai-models/ai-catalog.json")
    try:
        recs = json.load(open(p))["records"]
    except Exception:
        return []
    pool = []
    for r in recs:
        try:
            aid, name, desc = r["ID"], r["NAME"], r.get("DESCRIPTION", "")
        except Exception:
            continue
        pool.append((str(aid), str(name), str(desc)[:300], AI_URL + str(aid)))
    return _cap(pool)


def _mall_pool():
    p = os.path.join(WS, "signature-cyber-mega-mall/products.json")
    try:
        prods = json.load(open(p))
    except Exception:
        return []
    pool = []
    for r in prods:
        try:
            pid, name, blurb = r["id"], r["n"], r.get("b", "")
        except Exception:
            continue
        pool.append((str(pid), str(name), str(blurb)[:300],
                     MALL_URL + "?product=" + str(pid)))
    return _cap(pool)


def build_pools():
    spec = _spec_pool()
    patent = _patent_pool()
    pools = {
        "spec": spec,
        "wiki": _wiki_pool(spec, patent),
        "leaks": _leaks_pool(),
        "patent": patent,
        "ai": _ai_pool(),
        "mall": _mall_pool(),
    }
    return pools


def pick(pool, kind, book_idx):
    h = int(hashlib.sha1(f"{kind}:{book_idx}".encode()).hexdigest(), 16)
    return pool[h % len(pool)]


STOP = {"the", "a", "an", "of", "and", "for", "in", "on", "to", "with",
        "using", "use", "based", "from", "by", "via", "its", "their"}
# generic patent/spec jargon that makes bad titles and story objects
JUNK = {"method", "methods", "apparatus", "device", "devices", "system",
        "systems", "optionally", "substituted", "thereof", "wherein", "therein",
        "thereby", "therefor", "therewith", "comprising", "thereon", "thereinto"}


def rec_terms(title, k=6):
    words = re.findall(r"[A-Za-z][A-Za-z\-']+", title)
    out = []
    for w in words:
        wl = w.lower()
        if len(wl) > 3 and wl not in STOP and wl not in JUNK and wl not in out:
            if wl.endswith("ly") and len(out) < 2:
                continue  # adverbs make poor title words
            out.append(wl)
        if len(out) >= k:
            break
    return out


def rec_short(title, n=6):
    words = re.findall(r"[A-Za-z][A-Za-z\-']+", title)
    return " ".join(words[:n])
