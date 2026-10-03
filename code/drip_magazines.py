#!/usr/bin/env python3
"""
Signature Magazines - deterministic magazine-issue drip generator.

Usage:
    python3 code/drip_magazines.py --n 1000     # seed the magazine wing
    python3 code/drip_magazines.py --n 500      # cron: add more; IDs continue

Determinism: issue #i is always generated from seed SALT_M+i, so re-running
never changes an existing issue. New issues append into 100-issue gz chunks
under data/magazines/volumes/; data/magazines/index/mags.idx.json.gz is
extended; data/magazines/state.json tracks next_index.

All magazines are ORIGINAL generated works (invented topics, original
wording, general-knowledge explanations). No real-world publication names,
no trademarked characters. Every issue is labeled as a generated work.
Comics and newspapers are explicitly OUT of scope here (own sites).
"""
import argparse, gzip, json, os, random, datetime, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from trademark_safe import sanitize_book_text

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "magazines")
VOL = os.path.join(DATA, "volumes")
IDX = os.path.join(DATA, "index")
STATE_F = os.path.join(DATA, "state.json")
CHUNK = 100
SALT_M = 20261002
AUTHOR = "Justin Addam Higgins"
GEN_NOTE = ("An original generated work created by the Signature system. "
            "All names, topics, and events are invented; explanations are "
            "original wordings of general knowledge.")

MAGS = [
    ("science", "The Signature Science Review", "Science"),
    ("technology", "Signature Tech Monthly", "Technology"),
    ("arts", "The Signature Arts Journal", "Arts & Culture"),
    ("history", "The Signature Historical Record", "History"),
    ("invention", "The Inventor's Signature", "Invention"),
    ("nature", "The Signature Naturalist", "Nature"),
    ("space", "The Signature Cosmos", "Space"),
    ("math", "Signature Mathematics Quarterly", "Mathematics"),
    ("philosophy", "The Signature Thinker", "Philosophy"),
    ("kids", "Little Signatures", "Children's"),
]

# (topic, hook) banks — general-knowledge topics, original angles
TOPICS = {
"science": [
    ("Why the Sky Looks Blue", "sunlight scattering through the air"),
    ("How Bridges Carry Weight", "arches, trusses, and tension"),
    ("The Water Cycle, Step by Step", "evaporation to rainfall"),
    ("What Makes Magnets Stick", "domains inside iron"),
    ("How Plants Eat Sunlight", "photosynthesis in plain words"),
    ("Why Ice Floats", "the strange expansion of water"),
    ("Sound Waves You Can See", "vibration made visible"),
    ("The Science of Soap", "how bubbles lift dirt away"),
    ("Why Metals Conduct Heat", "free electrons on the move"),
    ("Clouds: Nature's Reservoirs", "how droplets gather and fall"),
    ("The Physics of a Bouncing Ball", "energy lost on every bounce"),
    ("How Thermometers Work", "expansion you can read"),
    ("Why Salt Melts Ice", "freezing point in action"),
    ("The Chemistry of Baking Bread", "yeast, gluten, and heat"),
    ("How Eyes Adjust to Darkness", "rods, cones, and patience"),
    ("Static Electricity Explained", "charges looking for balance"),
],
"technology": [
    ("How Computers Remember", "memory from switches to chips"),
    ("What Is an Algorithm?", "recipes the computer follows"),
    ("How Touchscreens Sense Fingers", "capacitance under glass"),
    ("The Journey of an Email", "packets across the world"),
    ("How GPS Finds You", "clocks in orbit"),
    ("Inside a Battery", "chemistry that pushes current"),
    ("What Makes Wi-Fi Work", "invisible waves, real rules"),
    ("How Digital Cameras See Color", "filters over tiny sensors"),
    ("The Logic of a Light Switch Network", "boolean ideas at home"),
    ("How Printers Place Ink", "dots too small to see"),
    ("Keeping Passwords Safe", "hashes, not secrets"),
    ("How Robots Balance", "sensors and quick corrections"),
    ("The Anatomy of a Microchip", "billions of tiny switches"),
    ("How Streaming Video Arrives", "compression and buffering"),
    ("Solar Panels, Plainly", "light knocked into current"),
    ("What Is Encryption?", "locks made of math"),
],
"arts": [
    ("Reading a Painting's Colors", "what palettes tell us"),
    ("The Architecture of a Song", "verse, chorus, and bridge"),
    ("How Stories Build Suspense", "the engine of page-turners"),
    ("The Craft of Pottery", "clay, wheel, and fire"),
    ("Understanding Perspective", "drawing depth on flat paper"),
    ("The Language of Dance", "movement as meaning"),
    ("How Poems Find Their Rhythm", "meter you can feel"),
    ("The Art of the Mural", "walls that speak"),
    ("Photography and Light", "painting with photons"),
    ("Theater's Invisible Crew", "the hands behind the curtain"),
    ("How Sculptors See Stone", "finding the form inside"),
    ("The Grammar of Film", "shots that tell stories"),
    ("Textiles as Storytelling", "patterns with memory"),
    ("The Joy of Sketching", "ten minutes, one pencil"),
    ("Music's Building Blocks", "notes, chords, and time"),
    ("How Choirs Blend Voices", "many throats, one sound"),
],
"history": [
    ("How Ancient Roads Were Built", "stone, survey, and sweat"),
    ("The Invention of Paper", "from pulp to page"),
    ("Lighthouses Through Time", "guiding ships home"),
    ("How Clocks Changed the Day", "from sundials to gears"),
    ("The Story of the Compass", "a needle finds north"),
    ("Markets of the Old World", "where trade routes met"),
    ("How Books Were Copied by Hand", "the scribe's long labor"),
    ("Bridges of the Ancient World", "spanning rivers with stone"),
    ("The History of the Map", "drawing what we know"),
    ("How Glass Was First Made", "sand, fire, and accident"),
    ("The Age of Windmills", "grinding grain with weather"),
    ("How Postal Systems Began", "letters on horseback"),
    ("The Story of Concrete", "Rome's lasting recipe"),
    ("How Harbors Grew Into Cities", "trade builds towns"),
    ("The History of the Calendar", "counting days together"),
    ("How Lenses Opened the Sky", "telescopes and new worlds"),
],
"invention": [
    ("The Idea Behind the Zipper", "small teeth, big convenience"),
    ("How Velcro Was Imagined", "burrs inspire a fastener"),
    ("The Paper Clip's Simplicity", "one wire, endless uses"),
    ("Inventing the Thermostat", "comfort on autopilot"),
    ("The Story of the Safety Pin", "a spring with manners"),
    ("How Eyeglasses Evolved", "clearer sight for all"),
    ("The Humble Umbrella", "a roof you can fold"),
    ("Inventing the Bicycle", "balance on two wheels"),
    ("The Telegraph's Dots and Dashes", "messages at wire speed"),
    ("How Refrigeration Works", "cold as a machine's promise"),
    ("The Sewing Machine's Stitch", "a needle that loops"),
    ("Inventing the Flashlight", "daylight in your pocket"),
    ("The Elevator's Brake", "safety that built skylines"),
    ("How Ballpoint Pens Flow", "a rolling ball of ink"),
    ("The Dishwasher's Spray", "cleaning with geometry"),
    ("Inventing the Smoke Detector", "a sentinel on the ceiling"),
],
"nature": [
    ("How Ants Organize", "a colony without bosses"),
    ("Why Birds Migrate", "seasons written in wings"),
    ("The Secret Life of Soil", "a world underfoot"),
    ("How Spiders Spin Silk", "stronger than it looks"),
    ("Why Leaves Change Color", "the green mask slips away"),
    ("The Language of Bees", "dances that give directions"),
    ("How Rivers Shape Land", "slow water, patient carving"),
    ("The Night Shift: Owls", "hunting by hearing"),
    ("How Seeds Travel", "wind, water, and hitchhikers"),
    ("Coral Reefs, Explained", "cities built by tiny animals"),
    ("Why Volcanoes Erupt", "pressure finds a way out"),
    ("The Patience of Turtles", "slow and steady wins"),
    ("How Mushrooms Spread", "the forest's hidden web"),
    ("Tides: The Moon's Pull", "oceans breathing twice a day"),
    ("How Camouflage Works", "hiding in plain sight"),
    ("The Water Bear's Superpower", "surviving almost anything"),
],
"space": [
    ("How Rockets Escape Earth", "pushing against nothing"),
    ("Why the Moon Has Phases", "sunlight's monthly show"),
    ("The Lives of Stars", "birth, burning, and farewell"),
    ("How Telescopes Gather Light", "bigger buckets for starlight"),
    ("What Is Gravity?", "the universe's gentle grip"),
    ("The Planets, In Order", "a tour of our neighborhood"),
    ("How Astronauts Sleep in Space", "strapped in among stars"),
    ("Comets: Icy Wanderers", "tails of ancient ice"),
    ("Why Mars Looks Red", "rust on a planetary scale"),
    ("The Speed of Light", "the universe's speed limit"),
    ("How Satellites Stay Up", "falling forever, missing Earth"),
    ("Black Holes, Plainly", "where gravity wins completely"),
    ("The International Space Station", "a house above the sky"),
    ("How Eclipses Happen", "shadows in alignment"),
    ("What Are Galaxies?", "islands of a billion suns"),
    ("Space Suits: Wearable Ships", "one person, one spacecraft"),
],
"math": [
    ("What Is Pi, Really?", "the circle's constant companion"),
    ("How Fractions Work", "pieces of a whole"),
    ("The Beauty of Prime Numbers", "numbers that won't split"),
    ("Understanding Percentages", "parts per hundred"),
    ("How Graphs Tell Stories", "pictures of numbers"),
    ("The Logic of Puzzles", "thinking in steps"),
    ("What Is Infinity?", "bigger than big"),
    ("How Symmetry Shows Up", "mirrors in math and nature"),
    ("Counting Like a Computer", "the power of two"),
    ("The Magic of Multiplication Tables", "patterns that repeat"),
    ("How Probability Works", "measuring maybe"),
    ("Geometry in Your Kitchen", "shapes everywhere"),
    ("What Are Negative Numbers?", "below zero and proud"),
    ("How Averages Can Mislead", "one number, many stories"),
    ("The Fibonacci Pattern", "nature's favorite sequence"),
    ("Solving for X", "the detective work of algebra"),
],
"philosophy": [
    ("What Is Fairness?", "an old question, fresh eyes"),
    ("How Do We Know Things?", "the puzzle of knowledge"),
    ("What Makes a Good Friend?", "thinking about friendship"),
    ("Is It Okay to Change Your Mind?", "the virtue of rethinking"),
    ("What Is Courage?", "fear, faced well"),
    ("How Should We Spend Time?", "the ethics of hours"),
    ("What Is Truth?", "matching words to world"),
    ("Why Be Kind?", "reasons for gentleness"),
    ("What Makes Something Beautiful?", "taste and its puzzles"),
    ("How Do We Make Choices?", "freedom and its weight"),
    ("What Is a Good Life?", "many answers, one question"),
    ("Why Do Rules Matter?", "order and its reasons"),
    ("What Is Imagination For?", "the mind's workshop"),
    ("How Do We Learn From Mistakes?", "failure as teacher"),
    ("What Is Wisdom?", "knowledge, ripened"),
    ("Why Ask Why?", "curiosity's defense"),
],
"kids": [
    ("How to Grow a Bean in a Cup", "a windowsill experiment"),
    ("Why Do We Dream?", "movies of the sleeping mind"),
    ("Making Shadow Puppets", "hands become animals"),
    ("How to Write a Secret Code", "ciphers for beginners"),
    ("Why Do Balloons Pop?", "pressure's loud exit"),
    ("Building a Blanket Fort", "engineering with cushions"),
    ("How to Draw a Cat", "circles become whiskers"),
    ("Why Is the Ocean Salty?", "a very old recipe"),
    ("Making Music With Jars", "water sets the pitch"),
    ("How to Press Flowers", "saving summer in a book"),
    ("Why Do We Sneeze?", "the nose's big reset"),
    ("Building a Paper Airplane", "folding for distance"),
    ("How to Tell Time by the Sun", "shadows as clocks"),
    ("Why Do Stars Twinkle?", "air wobbling starlight"),
    ("Making a Bird Feeder", "lunch for feathered friends"),
    ("How to Keep a Nature Journal", "noticing the wild"),
],
}

INTROS = [
    "Every issue of ours starts with curiosity, and this month {t} gave us plenty. {h} — simple to say, richer to understand.",
    "{T} sounds simple until you look closer. This month we follow the thread of {h} to see where it leads.",
    "Some topics announce themselves loudly; {t} whispers. Listen in as we unpack {h}.",
    "Readers wrote in asking about {t}, so we did what we always do: we asked how, why, and what next. The short answer starts with {h}.",
    "{T} is one of those everyday wonders hiding in plain sight. The key to it is {h}.",
    "Open any window, step outside, and {t} is there waiting. What follows is the story of {h}.",
    "We chose {t} for this issue because it rewards a second look. At its heart lies {h}.",
    "Few subjects are as satisfying to unravel as {t}. The first thread to pull is {h}.",
]
BODIES = [
    "Start with the basics. {h} means that small causes add up: each piece does a little, and together they do a lot. Watch for this pattern and {t} stops being mysterious — it becomes mechanical, in the best sense.",
    "Here is a way to see it yourself. The next time you meet {t} in daily life, pause and ask what is pushing, pulling, heating, or carrying. The answer is almost always {h}, working quietly in the background.",
    "It helps to compare. Think of {t} the way you think of a familiar tool: it has a job, parts that do the job, and limits. {H} is the part most people miss, and once you see it, the whole thing clicks.",
    "Scientists and builders describe {t} with careful words, but the picture is friendly: {h}. Hold that picture while you read on, and the details will arrange themselves around it.",
    "A common mistake is to think {t} happens all at once. It doesn't — it happens in steps, each one setting up the next. {H} is usually the step where everything changes.",
    "Try explaining {t} to a friend in one sentence. The best one-sentence version we found leans on {h} — and if your friend nods, you understand it well enough to use it.",
    "History adds flavor here: people noticed {t} long before they could explain it. The explanation, when it came, turned out to be {h} — simple at the core, elaborate at the edges.",
    "There is a hands-on side too. You can explore {t} with household things and a little patience; what you will find, again and again, is {h} doing the heavy lifting.",
]
CLOSERS = [
    "So the next time {t} crosses your path, you will know what to look for — and knowing is the best part of the show.",
    "That is {t} in a nutshell: {h}, unfolding one step at a time. Keep wondering.",
    "From here, {t} is yours to explore. Start with {h}, and follow your curiosity outward.",
    "And that is the whole trick of {t} — {h}, hiding in plain sight all along.",
    "Keep this issue on the shelf; {t} will look different the second time you read about it. {H} tends to do that.",
    "Questions welcome — that is what the margins are for. {T} rewards every reader who asks why.",
]

DEPTS = ["Cover Story", "In Depth", "How It Works", "Field Notes", "The Big Picture"]

class G:
    def __init__(self, seed):
        self.r = random.Random(seed)
    def pick(self, seq):
        return seq[self.r.randrange(len(seq))]
    def sample(self, seq, k):
        return self.r.sample(seq, k)
    def num(self, a, b):
        return self.r.randint(a, b)

def words_of(text):
    return len(text.split())

def fill(tpl, **kw):
    out = tpl
    for k, v in kw.items():
        out = out.replace("{" + k + "}", str(v))
    return out

def make_issue(idx):
    g = G(SALT_M + idx)
    mi = (idx - 1) % len(MAGS)
    skey, magname, sname = MAGS[mi]
    seqno = (idx - 1) // len(MAGS) + 1
    vol = (seqno - 1) // 12 + 1
    no = (seqno - 1) % 12 + 1
    # monthly date, backdated from Oct 2026
    months_back = (idx - 1) // len(MAGS)
    y, m = 2026, 10 - months_back
    while m < 1:
        m += 12; y -= 1
    date = f"{y:04d}-{m:02d}-{g.num(1,28):02d}"
    topics = g.sample(TOPICS[skey], 5)
    articles = []
    for ai, (topic, hook) in enumerate(topics):
        t_cap = topic[0].upper() + topic[1:]
        h_cap = hook[0].upper() + hook[1:]
        intro = fill(g.pick(INTROS), t=topic, T=t_cap, h=hook, H=h_cap)
        b1 = fill(g.pick(BODIES), t=topic, T=t_cap, h=hook, H=h_cap)
        b2 = fill(g.pick(BODIES), t=topic, T=t_cap, h=hook, H=h_cap)
        closer = fill(g.pick(CLOSERS), t=topic, T=t_cap, h=hook, H=h_cap)
        body = intro + "\n\n" + b1 + "\n\n" + b2 + "\n\n" + closer
        headline, bdy = sanitize_book_text(topic, g)[0], sanitize_book_text(body, g)[0]
        articles.append({"t": headline, "d": DEPTS[ai % len(DEPTS)], "b": bdy,
                         "a": "Signature Editorial Staff"})
    cover = f"Vol. {vol}, No. {no} — {magname}: {articles[0]['t']}, plus {len(articles)-1} more features."
    cover, desc = sanitize_book_text(cover, g)[0], sanitize_book_text(
        f"The {date} issue of {magname} ({sname}): five original features — " +
        ", ".join(a["t"] for a in articles) + ".", g)[0]
    words = sum(words_of(a["b"]) + words_of(a["t"]) for a in articles) + words_of(cover) + words_of(desc)
    return {
        "id": f"JAH-MAG-{idx:06d}", "mag": magname, "mkey": skey,
        "subject": sname, "vol": vol, "no": no, "date": date,
        "cover": cover, "desc": desc, "words": words,
        "articles": articles, "note": GEN_NOTE,
    }

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
    return os.path.join(VOL, f"mags-c{n:05d}.json.gz")

def idx_entry(rec):
    return {"id": rec["id"], "m": rec["mag"], "s": rec["subject"],
            "v": rec["vol"], "n": rec["no"], "d": rec["date"],
            "w": rec["words"], "desc": rec["desc"],
            "at": [a["t"] for a in rec["articles"]]}

def load_idx():
    p = os.path.join(IDX, "mags.idx.json.gz")
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_idx(entries):
    with gzip.open(os.path.join(IDX, "mags.idx.json.gz"), "wt", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, separators=(",", ":"))

def write_api(total, words, per_mag, n_chunks):
    api = {"site": "The Signature Book Depository — Magazines",
           "total_issues": total, "total_words": words,
           "magazines": per_mag, "chunks": n_chunks, "chunk_size": CHUNK,
           "march_goal": 1000000,
           "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "index": "data/magazines/index/mags.idx.json.gz",
           "note": "All magazine issues are original generated works by/for the Signature system."}
    with open(os.path.join(IDX, "api.json"), "w") as f:
        json.dump(api, f, ensure_ascii=False, indent=1)

def run(n):
    os.makedirs(VOL, exist_ok=True)
    os.makedirs(IDX, exist_ok=True)
    st = load_state()
    start, end = st["next_index"], st["next_index"] + n
    entries = load_idx()
    per_mag = {}
    for e in entries:
        per_mag[e["m"]] = per_mag.get(e["m"], 0) + 1
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
        rec = make_issue(idx)
        buf.append(rec)
        entries.append(idx_entry(rec))
        per_mag[rec["mag"]] = per_mag.get(rec["mag"], 0) + 1
        total_words += rec["words"]
        new_recs += 1
        if len(buf) + (len(last_partial) if last_partial else 0) >= CHUNK or \
           ((start - 1 + new_recs) % CHUNK == 0):
            flush()
        if new_recs % 250 == 0:
            print(f"  ... {new_recs}/{n} issues", flush=True)
    if buf or last_partial is not None:
        flush()
    n_chunks = (end - 2) // CHUNK + 1 if end > 1 else 0
    save_idx(entries)
    write_api(end - 1, total_words, per_mag, n_chunks)
    st["next_index"] = end
    save_state(st)
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("sitemap_all", os.path.join(HERE, "sitemap_all.py"))
    _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod); _mod.write_sitemap()
    print(f"done: issues {start}..{end-1} ({new_recs} new), total {end-1}, words {total_words}, chunks {n_chunks}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    a = ap.parse_args()
    run(a.n)

if __name__ == "__main__":
    main()
