#!/usr/bin/env python3
"""
Signature Library Artifacts - deterministic drip generator for the library
wing of The Signature Book Depository.

Usage:
    python3 code/drip_artifacts.py --n 500      # seed the library wing
    python3 code/drip_artifacts.py --n 300      # cron: add more; IDs continue

Determinism: artifact #i is always generated from seed SALT_L+i. New
artifacts append into 100-artifact gz chunks under data/library/volumes/;
data/library/index/libs.idx.json.gz is extended; data/library/state.json
tracks next_index.

Artifact kinds (all Signature versions of what a great library holds):
  microfilm  - archive reels: indexed frames pointing at Signature records
  atlas      - atlases of the invented Signature world (original geography)
  manuscript - short original manuscripts
  reference  - reference volumes: original general-knowledge entries
  special    - special themed collections

Everything is original generated content, trademark-sanitized. No real
places, people, or publication names.
"""
import argparse, gzip, json, os, random, datetime, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from trademark_safe import sanitize_book_text

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "library")
VOL = os.path.join(DATA, "volumes")
IDX = os.path.join(DATA, "index")
STATE_F = os.path.join(DATA, "state.json")
CHUNK = 100
SALT_L = 20261003
GEN_NOTE = ("An original generated work created by the Signature system. "
            "All names, places, and records described are invented.")

KINDS = [
    ("microfilm", "Signature Microfilm Reel", "Microfilm"),
    ("atlas", "Signature World Atlas", "Atlas"),
    ("manuscript", "Signature Manuscript", "Manuscript"),
    ("reference", "Signature Reference Volume", "Reference"),
    ("special", "Signature Special Collection", "Special Collection"),
]

# invented Signature-world geography (original, no real places)
REGIONS = [
    ("Auroria", "northern highlands of rolling signal-fields"),
    ("Cinderfall", "volcanic lowlands where glass-sand is harvested"),
    ("The Verdant Reach", "dense canopy forests along the slow rivers"),
    ("Meridian Flats", "salt plains crossed by the old survey lines"),
    ("Gloaming Coast", "cliff shores where the light lingers longest"),
    ("The Hollow Peaks", "mountains honeycombed with echo caves"),
    ("Sable Dunes", "singing deserts of black silica"),
    ("The Lantern Isles", "an archipelago of lighthouse settlements"),
    ("Frostbound Marches", "glacial steppes at the world's roof"),
    ("The Emberwood", "forests of slow-burning heartwood trees"),
    ("Pale Expanse", "tundra where the aurora touches ground"),
    ("The Shattered Delta", "a river broken into a thousand mouths"),
    ("Ironhold Valley", "canyon towns built around the old forges"),
    ("The Mistral Downs", "windswept chalk hills and sheepfolds"),
    ("Coral Bastion", "a reef-city grown, not built"),
    ("The Quiet Interior", "vast grasslands with no roads at all"),
    ("Stormwatch Head", "a cape famous for its weather towers"),
    ("The Gilded Basin", "amber fields in the continental bowl"),
    ("Twilight Fen", "marshlands of mirror-still water"),
    ("The Obsidian Shelf", "a plateau of black volcanic glass"),
    ("Harborlight", "the great estuary port of the west"),
    ("The Sunken Library Coast", "cliffs holding the old archive caves"),
    ("The Copper Hills", "terraced mines turned to gardens"),
    ("The Far Pastures", "high meadows beyond the last fence"),
]
REGION_NOTES = [
    "Surveyed in the early Signature expeditions; known for its {f}.",
    "Travelers come for the {f}, and stay for the quiet.",
    "The old charts mark it well: {f} as far as the eye reaches.",
    "Local guides say the {f} here are unlike anywhere else.",
    "Cartographers' favorite: {f} drawn in unusual detail.",
    "A region defined by its {f} — unmistakable once seen.",
]
REGION_FEATS = ["signal-towers", "glass markets", "river festivals", "echo choirs",
                "dune sailors", "lighthouse keepers", "frost fairs", "ember kilns",
                "aurora watchers", "delta pilots", "forge museums", "chalk figures",
                "reef gardens", "grassland riders", "storm readers", "amber traders",
                "mirror regattas", "obsidian carvers", "harbor bells", "archive divers",
                "copper terraces", "meadow fairs"]

# reference-volume topics (general knowledge, original wording)
REF_TOPICS = [
    ("Adhesion", "the tendency of unlike surfaces to cling"),
    ("Buoyancy", "why some things float and others sink"),
    ("Capillarity", "how liquids climb narrow tubes"),
    ("Diffraction", "waves bending around corners"),
    ("Erosion", "the slow sculpture of wind and water"),
    ("Fermentation", "microbes turning sugar into flavor"),
    ("Germination", "a seed's first decision to grow"),
    ("Humidity", "water hiding in the air"),
    ("Inertia", "objects preferring to keep doing what they're doing"),
    ("Junctions", "where two different things meet and mix"),
    ("Kinematics", "describing motion without asking why"),
    ("Lubrication", "the diplomacy of sliding surfaces"),
    ("Magnetism", "invisible attraction with strict manners"),
    ("Nucleation", "how crystals find a place to begin"),
    ("Osmosis", "water seeking balance through membranes"),
    ("Polarization", "light learning to line up"),
    ("Quenching", "hot metal's sudden cold bath"),
    ("Refraction", "light bending at the border of mediums"),
    ("Sedimentation", "particles settling out of suspension"),
    ("Turbulence", "orderly flow breaking into chaos"),
    ("Ultraviolet", "light just beyond violet's edge"),
    ("Viscosity", "a fluid's reluctance to flow"),
    ("Wavelength", "the distance between wave crests"),
    ("Xylem", "a plant's upward plumbing"),
    ("Yield", "how much you get for what you put in"),
    ("Zenith", "the point directly overhead"),
    ("Alloy", "metals improved by company"),
    ("Brine", "water made serious by salt"),
    ("Catalyst", "a helper that isn't consumed"),
    ("Dewpoint", "when air must surrender its water"),
]
REF_TMPL = [
    "{T}: {h}. In practice this means small differences add up — watch a {t} at work and you will see the same pattern repeat at every scale.",
    "{T} deserves a plain explanation: {h}. Once that picture is steady in mind, the details arrange themselves without effort.",
    "To understand {t}, follow the energy. {H} — and everything else is commentary on that single fact.",
    "{T} shows up in kitchens, workshops, and weather alike. The common thread is {h}, doing quiet work everywhere.",
]

MANUSCRIPT_THEMES = [
    ("The Cartographer's Daughter", "a mapmaker's child redraws the world"),
    ("A Field Guide to Small Hours", "notes from a night-shift naturalist"),
    ("The Glassblower's Ledger", "a craftsman's year in furnaces"),
    ("Letters Never Sent", "correspondence across imagined distances"),
    ("The Orchard Keeper", "seasons of grafting and patience"),
    ("A Treatise on Quiet Machines", "on devices that work unnoticed"),
    ("The Beekeeper's Almanac", "a year among the hives"),
    ("Songs for the Long Winter", "a songbook of cold months"),
    ("The Archivist's Dream", "a keeper who catalogs clouds"),
    ("A Manual for Wanderers", "practical philosophy of the road"),
    ("The Clockmaker's Garden", "where gears meet growing things"),
    ("Notes Toward a Kinder City", "an urban planner's sketches"),
]
MS_PARAS = [
    "It began, as many true things do, with attention. {h} — and from that small noticing, everything else followed.",
    "The days took their shape around the work. Mornings were for {t}; afternoons for wondering what the mornings had meant.",
    "There is a patience to this craft that no hurried hand can fake. {H}, practiced daily, becomes a kind of devotion.",
    "Neighbors asked what it was all for. The honest answer — {h} — satisfied some and puzzled others, which seemed exactly right.",
    "By the turning of the season the work had changed its maker as much as its material. {T} leaves marks on everyone who tends it.",
    "The final pages were written slowly, the way one closes a good door: {h}, and then quiet.",
]

SPECIAL_THEMES = [
    ("The Invention Sketchbooks", "early drawings from Signature workshops"),
    ("Voices of the Builders", "oral histories of the first makers"),
    ("The Pattern Archive", "textile and tile designs through the years"),
    ("Maps of Imagined Places", "cartography of the invented world"),
    ("The Recipe Manuscripts", "kitchen notebooks of the Signature kitchens"),
    ("Letters from the Field", "correspondence of traveling naturalists"),
    ("The Tool Museum Papers", "histories of humble instruments"),
    ("Songs of the Workshops", "work-songs collected across the trades"),
]

class G:
    def __init__(self, seed):
        self.r = random.Random(seed)
    def pick(self, seq):
        return seq[self.r.randrange(len(seq))]
    def sample(self, seq, k):
        return self.r.sample(seq, k)
    def num(self, a, b):
        return self.r.randint(a, b)
    def shuffled(self, seq):
        s = list(seq); self.r.shuffle(s); return s

def words_of(t):
    return len(t.split())

def fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace("{" + k + "}", str(v))
    return tpl

def _clean(text, g):
    return sanitize_book_text(text, g)[0]

def _spec_id(g):
    # deterministic invented record reference for microfilm frames
    kind = g.pick(["JAH-SPEC", "JAH-BOOK", "JAH-PAT"])
    return f"{kind}-{g.num(1, 600000):06d}"

def make_microfilm(g, idx, seqno):
    frames = []
    for f in range(40):
        rid = _spec_id(g)
        what = g.pick(["title page and abstract", "claims summary", "figure plates",
                       "inventor's notes", "revision history", "index entries",
                       "cross-references", "cover sheet"])
        frames.append({"f": f + 1, "ref": rid,
                       "d": _clean(f"Frame {f+1}: {what} of record {rid}, preserved at archival density.", g)})
    title = _clean(f"Microfilm Reel {seqno:04d} — Signature Records Archive", g)
    desc = _clean(f"Archival microfilm reel {seqno:04d}: 40 indexed frames preserving Signature records "
                  f"({_spec_id(g)} through {_spec_id(g)}) at 24x reduction, with frame-level index.", g)
    return title, desc, [{"t": "Frames", "items": frames}]

def make_atlas(g, idx, seqno):
    regions = g.sample(REGIONS, 12)
    entries = []
    for name, geo in regions:
        note = fill(g.pick(REGION_NOTES), f=g.pick(REGION_FEATS))
        entries.append({"n": name,
                        "d": _clean(f"{name}: {geo}. {note}", g)})
    title = _clean(f"Signature World Atlas, Plate Set {seqno:03d}", g)
    desc = _clean(f"Twelve surveyed regions of the invented Signature world — {', '.join(r[0] for r in regions[:4])}, and more — with surveyor's notes.", g)
    return title, desc, [{"t": "Regions", "items": entries}]

def make_manuscript(g, idx, seqno):
    theme, hook = g.pick(MANUSCRIPT_THEMES)
    chs = []
    for c in range(6):
        body = "\n\n".join(fill(g.pick(MS_PARAS), t=theme.lower(), T=theme, h=hook, H=hook[0].upper() + hook[1:]) for _ in range(3))
        chs.append({"t": _clean(f"Chapter {c+1}", g), "b": _clean(body, g)})
    title = _clean(theme + f" (MS-{seqno:04d})", g)
    desc = _clean(f"An original manuscript: {theme} — {hook}. Six chapters, hand-style setting.", g)
    return title, desc, [{"t": "Chapters", "items": chs}]

def make_reference(g, idx, seqno):
    topics = g.sample(REF_TOPICS, 20)
    entries = []
    for topic, hook in topics:
        t_cap = topic[0].upper() + topic[1:]
        h_cap = hook[0].upper() + hook[1:]
        body = fill(g.pick(REF_TMPL), t=topic.lower(), T=t_cap, h=hook, H=h_cap)
        entries.append({"t": _clean(topic, g), "b": _clean(body, g)})
    letter = chr(65 + (seqno - 1) % 26)
    title = _clean(f"Signature Reference Volume {seqno:03d} — {letter}", g)
    desc = _clean(f"Twenty original reference entries: {', '.join(t[0] for t in topics[:5])}, and more.", g)
    return title, desc, [{"t": "Entries", "items": entries}]

def make_special(g, idx, seqno):
    theme, hook = g.pick(SPECIAL_THEMES)
    items = []
    for i in range(16):
        items.append({"t": _clean(f"Item {i+1}", g),
                      "d": _clean(f"{theme} — item {i+1} of 16: {hook}; cataloged with provenance notes.", g)})
    title = _clean(f"{theme} — Collection {seqno:03d}", g)
    desc = _clean(f"A special collection: {theme}. {hook.capitalize()}. Sixteen cataloged items.", g)
    return title, desc, [{"t": "Items", "items": items}]

MAKERS = {"microfilm": make_microfilm, "atlas": make_atlas,
          "manuscript": make_manuscript, "reference": make_reference,
          "special": make_special}

def make_artifact(idx):
    g = G(SALT_L + idx)
    ki = (idx - 1) % len(KINDS)
    kkey, ktitle, kname = KINDS[ki]
    seqno = (idx - 1) // len(KINDS) + 1
    title, desc, sections = MAKERS[kkey](g, idx, seqno)
    words = words_of(title) + words_of(desc)
    flat_sections = []
    for s in sections:
        items = []
        for it in s["items"]:
            if "b" in it:
                items.append({"t": it["t"], "b": it["b"]})
                words += words_of(it["t"]) + words_of(it["b"])
            elif "d" in it:
                items.append({"t": it.get("n") or it.get("t") or it.get("f") and f"Frame {it['f']}" or it.get("ref"),
                              "b": it["d"]})
                words += words_of(it["d"])
            else:
                items.append({"t": it.get("ref", "?"), "b": it.get("d", "")})
        flat_sections.append({"t": s["t"], "items": items})
    return {"id": f"JAH-LIB-{idx:06d}", "kind": kname, "kkey": kkey,
            "title": title, "desc": desc, "words": words,
            "sections": flat_sections, "note": GEN_NOTE}

# ---------------------------------------------------------------- persistence

def load_state():
    if os.path.exists(STATE_F):
        with open(STATE_F) as f:
            return json.load(f)
    return {"next_index": 1}

def save_state(st):
    with open(STATE_F, "w") as f:
        json.dump(st, f)

def chunk_path(n):
    return os.path.join(VOL, f"libs-c{n:05d}.json.gz")

def idx_entry(rec):
    heads = []
    for s in rec["sections"]:
        heads += [i["t"] for i in s["items"][:8]]
    return {"id": rec["id"], "k": rec["kind"], "t": rec["title"],
            "d": rec["desc"], "w": rec["words"], "h": heads}

def load_idx():
    p = os.path.join(IDX, "libs.idx.json.gz")
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_idx(entries):
    with gzip.open(os.path.join(IDX, "libs.idx.json.gz"), "wt", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, separators=(",", ":"))

def write_api(total, words, per_kind, n_chunks):
    api = {"site": "The Signature Book Depository — Library",
           "total_artifacts": total, "total_words": words,
           "kinds": per_kind, "chunks": n_chunks, "chunk_size": CHUNK,
           "march_goal": 1000000,
           "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "index": "data/library/index/libs.idx.json.gz",
           "note": "All library artifacts are original generated works by/for the Signature system."}
    with open(os.path.join(IDX, "api.json"), "w") as f:
        json.dump(api, f, ensure_ascii=False, indent=1)

def run(n):
    os.makedirs(VOL, exist_ok=True)
    os.makedirs(IDX, exist_ok=True)
    st = load_state()
    start, end = st["next_index"], st["next_index"] + n
    entries = load_idx()
    per_kind = {}
    for e in entries:
        per_kind[e["k"]] = per_kind.get(e["k"], 0) + 1
    total_words = sum(e["w"] for e in entries)
    buf, chunk_no, last_partial = [], (start - 1) // CHUNK + 1, None
    if start > 1 and (start - 1) % CHUNK:
        p = chunk_path(chunk_no)
        if os.path.exists(p):
            with gzip.open(p, "rt", encoding="utf-8") as f:
                last_partial = json.load(f)

    def flush():
        nonlocal buf, chunk_no, last_partial
        recs = (last_partial + buf) if last_partial is not None else buf
        last_partial = None
        with gzip.open(chunk_path(chunk_no), "wt", encoding="utf-8") as f:
            json.dump(recs, f, ensure_ascii=False, separators=(",", ":"))
        buf = []
        chunk_no += 1

    new_recs = 0
    for idx in range(start, end):
        rec = make_artifact(idx)
        buf.append(rec)
        entries.append(idx_entry(rec))
        per_kind[rec["kind"]] = per_kind.get(rec["kind"], 0) + 1
        total_words += rec["words"]
        new_recs += 1
        if len(buf) + (len(last_partial) if last_partial else 0) >= CHUNK or \
           ((start - 1 + new_recs) % CHUNK == 0):
            flush()
        if new_recs % 250 == 0:
            print(f"  ... {new_recs}/{n} artifacts", flush=True)
    if buf or last_partial is not None:
        flush()
    n_chunks = (end - 2) // CHUNK + 1 if end > 1 else 0
    save_idx(entries)
    write_api(end - 1, total_words, per_kind, n_chunks)
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("sitemap_all", os.path.join(HERE, "sitemap_all.py"))
    _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod); _mod.write_sitemap()
    st["next_index"] = end
    save_state(st)
    print(f"done: artifacts {start}..{end-1} ({new_recs} new), total {end-1}, words {total_words}, chunks {n_chunks}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    a = ap.parse_args()
    run(a.n)

if __name__ == "__main__":
    main()
