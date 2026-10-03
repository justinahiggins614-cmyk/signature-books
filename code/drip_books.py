#!/usr/bin/env python3
"""
Signature Book Depository - deterministic book drip generator.

Usage:
    python3 code/drip_books.py --n 3000     # seed the depository
    python3 code/drip_books.py --n 1100     # cron: add more; IDs continue

Determinism: book #i is always generated from seed SALT+i, so re-running
never changes an existing book. New books append into 100-book gz chunks;
data/index/books.idx.json.gz is extended; data/index/api.json and
sitemap.xml are regenerated; data/state.json tracks next_index.

THE PROGRESS LOOP: every book carries an origin slot cycling the six
network sources (specs, JAH Wiki, JAH-N leaks, public patents, Telephone
Book AIs, Mega-Mall products) plus one standalone original. Pools rebuild
from the live sibling repos on every run (code/source_samplers.py), so new
catalog records automatically become eligible book seeds. Derived books
carry source-lineage links ("Based on ...") with stable #source-lineage
anchors on their ?book= pages.

All books are ORIGINAL generated works (author line: Justin Addam Higgins).
No real-world author names, no trademarked characters. Generated material
is labeled as generated on the site.
"""
import argparse, gzip, json, math, os, random, sys, datetime
from source_samplers import (build_pools, pick as pool_pick, rec_terms,
                             rec_short)
from trademark_safe import sanitize_book_text

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
VOL = os.path.join(DATA, "volumes")
IDX = os.path.join(DATA, "index")
STATE_F = os.path.join(DATA, "state.json")
CHUNK = 100
SALT = 20261001
AUTHOR = "Justin Addam Higgins"
GEN_NOTE = ("An original generated work created by the Signature system. "
            "All names, places, and events are invented.")

GENRES = [
    ("sf", "Science Fiction"), ("fantasy", "Fantasy"), ("mystery", "Mystery"),
    ("romance", "Romance"), ("horror", "Horror"),
    ("math", "Mathematics"), ("physics", "Physics"), ("chemistry", "Chemistry"),
    ("biology", "Biology"), ("history", "History"), ("cs", "Computer Science"),
    ("children", "Children's"), ("poetry", "Poetry"),
    ("manual", "Technical Manual"), ("philosophy", "Philosophy"),
    ("business", "Business"),
]
GNAME = dict(GENRES)

SEED_QUOTA = {"sf": 300, "fantasy": 300, "mystery": 260, "romance": 180,
              "horror": 180, "math": 180, "physics": 140, "chemistry": 140,
              "biology": 140, "history": 140, "cs": 180, "children": 300,
              "poetry": 200, "manual": 140, "philosophy": 130, "business": 90}

def _seed_pattern():
    # interleaved round-robin so the first books already span every genre
    pat, q = [], dict(SEED_QUOTA)
    while any(q.values()):
        for g, _ in GENRES:
            if q[g]:
                pat.append(g); q[g] -= 1
    return pat
SEED_PATTERN = _seed_pattern()
assert len(SEED_PATTERN) == 3000, len(SEED_PATTERN)

DRIP_CYCLE = []
for g, _ in GENRES:
    DRIP_CYCLE += [g] * max(1, SEED_QUOTA[g] // 10)

def genre_for(i):
    if i <= len(SEED_PATTERN):
        return SEED_PATTERN[i - 1]
    return DRIP_CYCLE[(i - len(SEED_PATTERN) - 1) % len(DRIP_CYCLE)]

# ---------------------------------------------------------------- pools

class G:
    """Per-book seeded generator."""
    def __init__(self, seed):
        self.r = random.Random(seed)
    def pick(self, seq):
        return self.r.choice(seq)
    def sample(self, seq, k):
        k = min(k, len(seq))
        return self.r.sample(list(seq), k)
    def num(self, a, b):
        return self.r.randint(a, b)
    def shuffled(self, seq):
        s = list(seq); self.r.shuffle(s); return s

import re
_CHOICE_RE = re.compile(r"\{([^{}]*\|[^{}]*)\}")
def fill(g, template, ctx):
    """Expand {a|b|c} choices with the book rng, then {slots} from ctx."""
    def _c(m):
        return g.pick(m.group(1).split("|"))
    t = _CHOICE_RE.sub(_c, template)
    try:
        t = t.format(**ctx)
    except KeyError:
        pass
    # safety net AFTER formatting: never emit doubled articles from slots
    t = t.replace("The the ", "The ").replace("the the ", "the ")
    return t

def words_of(text):
    return len(text.split())

# syllable pools for invented names (nothing resembling real authors)
NA = ["Ka", "Mi", "Ro", "Ta", "Se", "Lu", "Na", "Ve", "Ri", "Do", "Fa",
      "Ze", "O", "E", "A", "Sha", "Bel", "Cor", "Del", "Fen"]
NB = ["ren", "sha", "dor", "ven", "mir", "tal", "nor", "lia", "kem", "dara",
      "thon", "wick", "mar", "ston", "fell", "gwen", "hal", "bris", "cott", "mere"]
def person_name(g):
    a = g.pick(NA); b = g.pick(NB)
    first = (a + b).capitalize()
    last = g.pick(NA).capitalize() + g.pick(NB)
    return first + " " + last.capitalize()

def unique_names(g, n):
    out, seen = [], set()
    while len(out) < n:
        nm = person_name(g)
        if nm not in seen:
            seen.add(nm); out.append(nm)
    return out

# ---------------------------------------------------------------- fiction banks

CORE_SENT = [
    "{hero} {woke|woke up|stirred|rose} before dawn, the way {hero} always did when something was about to change.",
    "The {obj} had been {lost|hidden|missing|waiting} for years, and everyone in {home} knew the stories.",
    "{ally} arrived with {news|word|a warning|a map}, breathless and {pale|wide-eyed|laughing|solemn}.",
    "Nobody in {home} {believed|trusted|welcomed|understood} strangers, but {hero} was no ordinary stranger.",
    "The road to {dest} was {long|dangerous|forbidden|forgotten}, and the {season} made it worse.",
    "{hero} packed {little|almost nothing|a small bag|only the essentials} and left {home} without saying goodbye.",
    "By midday the {sky|air|light|wind} had changed, and {ally} knew they were being {followed|watched|tested}.",
    "{foe} had agents everywhere, or so the {rumors|stories|whispers|songs} claimed.",
    "That evening, {hero} and {ally} {argued|talked late|made a plan|shared a meal} under unfamiliar stars.",
    "The {obj} {glowed|hummed|pulsed|trembled} faintly, as if it recognized {hero}.",
    "{hero} had never {wanted|asked for|imagined|feared} this, but the {obj} had chosen, and choice was a kind of gravity.",
    "In {home}, children still {sang|told stories|drew pictures|asked questions} about the {obj}.",
    "{ally} knew the old {paths|roads|tunnels|songs} through {dest}, the ones the maps had forgotten.",
    "The first {trial|test|night|storm} came sooner than anyone expected.",
    "{hero} {hesitated|stepped forward|looked back|stood still}, and in that pause the whole plan changed.",
    "{foe} sent {a messenger|a warning|an offer|a threat} that {hero} could not ignore.",
    "What {ally} had not told {hero} was the {truth|secret|cost|history} of the {obj}.",
    "The {season} turned, and with it the {mood|fortunes|tides|roads} of everyone traveling to {dest}.",
    "At the {border|crossing|gate|edge} of {dest}, they were {stopped|welcomed|questioned|recognized}.",
    "{hero} learned that the {obj} was not a {tool|treasure|weapon|key} at all, but a {promise|test|message|mirror}.",
    "Nights on the road were for {stories|planning|silence|watching the sky}, and {ally} had the best stories.",
    "The {foe} {moved|waited|planned|listened}, patient as {winter|stone|deep water|old grief}.",
    "{hero} dreamed of {home}, and woke with the {obj} {warm|cold|heavier|lighter} in {his_her} hands.",
    "Every {legend|story|song|map} agreed on one thing: the {obj} belonged in {dest}.",
    "They crossed the {river|ridge|desert|marsh} at dawn, {tired|hopeful|silent|singing}.",
    "{ally} {confessed|revealed|admitted|finally said} what {he_she} had been carrying all along.",
    "The plan was {simple|mad|fragile|brilliant}: reach {dest} before the {foe} did.",
    "{hero} counted {supplies|stars|steps|reasons to turn back} and kept walking anyway.",
    "In {dest}, the {obj} would either {save|doom|free|change} everything. Nobody knew which.",
    "The {storm|silence|crowd|dark} broke, and suddenly there was no more time for doubt.",
    "{foe} stood revealed at last, and {he_she2} was not what the {stories|legends|rumors} had promised.",
    "{hero} understood, all at once, what the {obj} had been trying to {say|teach|warn|show}.",
    "The {battle|bargain|choice|storm} lasted {minutes|hours|a single breath|all night}.",
    "{ally} {stood by|stepped in|paid the price|held the line} when it mattered most.",
    "{hero} {chose|refused|sacrificed|offered} the one thing {he_she} could not afford to lose.",
    "The {obj} {shattered|blazed|sang|went quiet}, and the {foe} {faltered|fled|laughed|wept}.",
    "Dawn came {soft|gray|golden|cold} over {dest}, and it was over.",
    "{hero} looked at what remained of the {obj} and {smiled|wept|laughed|bowed}.",
    "The road home to {home} felt {shorter|longer|different|sweeter} than the road out.",
    "{ally} stayed in {dest}, or so the {story|song|record} goes.",
    "Years later, in {home}, they still {tell|sing|argue about|remember} what {hero} did.",
    "The {obj} was {gone|restored|hidden again|never found}, but its {lesson|light|echo|story} remained.",
    "{hero} never {boasted|explained|regretted|forgot} that {season}.",
    "And somewhere beyond {dest}, the {wind|stars|sea|sky} kept the secret.",
    "{hero} {found|earned|accepted|refused} {peace|a new name|a quiet life|another road}.",
    "The {children|elders|travelers|skeptics} of {home} would ask, and {hero} would {smile|begin|nod slowly|tell it true}.",
    "What the {obj} had {cost|given|proven|hidden} could never quite be measured.",
    "But the {season} after, the {harvest|rains|stars|roads} were kinder, and people noticed.",
]

CORE_DIALOG = [
    '"We {go|leave|move} {now|at dawn|tonight}," {ally} said. "The {foe} {waits for no one|already knows|is close}."',
    '"{hero}," {ally} whispered, "the {obj} is {waking|changing|calling}. {Can you feel it|Do you hear it|Look}."',
    '"I did not {ask for|choose|want} this," {hero} said. "{But|Still|Yet} here we are."',
    '"Then we {do it together|finish it|go home|make our own road}," said {ally}.',
    '"You {cannot|must not|dare not} {trust|follow|fight|face} the {foe}," warned the {elder|keeper|stranger}.',
    '"{Watch|Listen|Remember|Hold on}," {hero} said, "{and|then} {do exactly as I do|run|do not look back}."',
]

GENRE_OVERLAY = {
 "sf": {
  "title": ["The {adj} {noun}", "Beyond the {noun}", "{noun} of {place}", "The {place} {noun}",
            "Echoes of the {noun}", "The Last {noun}", "{adj} {noun}", "Signal from {place}",
            "The {noun} Protocol", "Children of the {noun}", "{place}: {noun}", "The {adj} Horizon"],
  "adj": ["Quantum", "Stellar", "Neon", "Orbital", "Chrome", "Silent", "Hollow", "Electric", "Frozen", "Luminous", "Derelict", "Synthetic", "Crimson", "Distant"],
  "noun": ["Starship", "Signal", "Colony", "Horizon", "Engine", "Transmission", "Outpost", "Nebula", "Android", "Reactor", "Void", "Beacon", "Ark", "Relay"],
  "place": ["the Kepler Belt", "New Ceres Station", "the Andromeda Relay", "Port Meridian", "the Helios Array", "Vesta Prime", "the Long Dark", "Cryo Harbor", "Tessellate Nine"],
  "obj": ["the star chart", "the quantum core", "the last transmission", "the navigation key", "the seed vault", "the distress beacon", "the alien archive"],
  "foe": ["the rogue fleet", "the silent machines", "the Consortium", "the void-born", "the rust swarm"],
  "extra": [
    "The {noun} {drifted|burned|waited} in high orbit, {dark|lit|silent|scarred}.",
    "Shipboard {gravity|air|time} behaved strangely near the {obj}.",
    "{hero} ran the {diagnostic|numbers|simulation} three times. Same impossible result.",
    "The {foe} communicated in {bursts|silence|static|light}, and {ally} was learning to read it.",
    "Somewhere past {place}, physics filed a formal complaint.",
    "{hero} sealed the {airlock|hatch|bulkhead} and trusted the math.",
    "The colony's {reactor|dome|greenhouse|array} was failing, and only the {obj} could {restart|replace|explain} it.",
    "Stars looked {different|closer|wrong|beautiful} through the cracked viewport.",
  ]},
 "fantasy": {
  "title": ["The {adj} {noun}", "{noun} of {place}", "{hero}'s {noun}", "The {place} {noun}",
            "A {noun} of {noun2}", "The Last {noun}", "Where the {noun} {verb}", "The {adj} Crown",
            "Song of the {noun}", "The {noun} Throne", "Beyond {place}", "{adj} {noun2}"],
  "adj": ["Ancient", "Whispering", "Golden", "Shadowed", "Emerald", "Crimson", "Moonlit", "Forgotten", "Burning", "Silent", "Thorned", "Starlit"],
  "noun": ["Sword", "Crown", "Forest", "Tower", "Dragon", "Spell", "River", "Throne", "Amulet", "Gate", "Oath", "Harvest", "Mountain", "Well"],
  "noun2": ["Kings", "Ashes", "Thorns", "Echoes", "Embers", "Wolves", "Stars", "Tides"],
  "place": ["the Elderwood", "Dunmere Keep", "the Ashen Moors", "Thistledown Vale", "the Sunken Court", "Ravenscar", "the Glimmerfen", "High Aldermark"],
  "obj": ["the old sword", "the moonstone amulet", "the sealed letter", "the dragon egg", "the silver horn", "the map of lost roads"],
  "foe": ["the Usurper", "the Hollow King", "the Thorn Witch", "the iron warlord", "the pale council"],
  "verb": ["Sleeps", "Wakes", "Burns", "Sings", "Waits", "Falls"],
  "extra": [
    "Old {magic|runes|wards} still {held|slept|hummed} in the stones of {place}.",
    "{hero} spoke the {word|name|oath} and the {air|water|fire} listened.",
    "The {dragon|stag|raven|wolf} watched from the treeline, {curious|wary|ancient}.",
    "{ally} knew the {old songs|herb-lore|star-charts|sword-forms} of {home}.",
    "Magic had a {price|memory|taste|sound}, and {hero} was learning it.",
    "The {foe}'s {banners|spells|scouts} darkened the road to {dest}.",
    "In {dest}, the {throne|well|gate} remembered every {oath|king|name} ever spoken.",
  ]},
 "mystery": {
  "title": ["The {place} {noun}", "{noun} at {place}", "A {noun} in the {noun2}", "The {adj} {noun}",
            "Death of a {noun}", "The {noun} Affair", "Murder on the {noun}", "The {adj} Alibi",
            "What the {noun} {verb}", "The Last {noun} of {place}"],
  "adj": ["Silent", "Crooked", "Velvet", "Hollow", "Midnight", "Paper", "Glass", "Vanished", "Crimson", "Patient"],
  "noun": ["Letter", "Key", "Photograph", "Ledger", "Confession", "Inheritance", "Alibi", "Footprint", "Telegram", "Will", "Mask", "Clock"],
  "noun2": ["Fog", "Shadows", "Stairs", "Archive", "Harbor", "Theater"],
  "place": ["Blackwood Manor", "the Harborside Hotel", "Grimshaw Lane", "the old depot", "Candlewick Row", "the Marlowe Club", "Ferry Terminal Nine"],
  "obj": ["the missing ledger", "the torn photograph", "the unsigned letter", "the brass key", "the second will"],
  "foe": ["the blackmailer", "the silent partner", "the forger", "the vanished heir"],
  "verb": ["Hid", "Knew", "Saw", "Kept", "Buried"],
  "extra": [
    "The {clue} did not fit, and that was the most interesting thing about it.",
    "{hero} {reconstructed|re-read|photographed|pocketed} the {clue} before the police arrived.",
    "Everyone at {place} had a {reason|secret|alibi|grudge}.",
    "{ally} kept the {files|notes|ledger} in {perfect|chronological|suspicious} order.",
    "The {foe} had been {careful|clever|patient}, but not careful enough.",
    "{hero} noticed what was {missing|moved|wrong|too clean} about the {room|desk|scene}.",
    "Three {witnesses|suspects|lies} and only one truth, {ally} said.",
  ]},
 "romance": {
  "title": ["The {adj} {noun}", "{noun} at {place}", "A {season} of {noun}", "Where {noun} {verb}",
            "The {noun} Between Us", "{adj} {noun2}", "Letters from {place}", "The {place} {noun}"],
  "adj": ["Tender", "Wild", "Patient", "Golden", "Second", "Borrowed", "Endless", "Quiet", "Fierce", "Lucky"],
  "noun": ["Summer", "Letter", "Promise", "Garden", "Dance", "Harbor", "Song", "Kitchen", "Train", "Bookshop", "Rain", "Porch"],
  "noun2": ["Hearts", "Beginnings", "Chances", "Mornings", "Vows"],
  "place": ["Willow Creek", "the old bookshop", "Harbor Lane", "the farmers' market", "Cedar Falls", "the lighthouse cafe"],
  "obj": ["the unsent letter", "the old photograph", "the recipe box", "the train ticket", "the pressed flower"],
  "foe": ["doubt", "distance", "the past", "a misunderstanding", "fear"],
  "verb": ["Blooms", "Waits", "Returns", "Heals", "Begins"],
  "season": ["spring", "summer", "autumn", "winter"],
  "extra": [
    "{hero} {laughed|blushed|looked away|smiled} before {he_she} could stop {him_her}self.",
    "The {cafe|porch|garden} smelled of {rain|coffee|jasmine|fresh bread}, and {ally} was already there.",
    "Some {feelings|things|truths} arrive {quietly|suddenly|like weather|without permission}.",
    "{ally} left {a note|flowers|a book|coffee} where {hero} would find it.",
    "They {danced|talked|walked|cooked} until the {stars|streetlights|candles} came on.",
    "The {obj} {surfaced|returned|was found}, and with it everything unsaid.",
    "{hero} finally said the {thing|words} that had been waiting for years.",
  ]},
 "horror": {
  "title": ["The {adj} {noun}", "{noun} of {place}", "The {place} {noun}", "What {verb} in the {noun}",
            "The Last {noun}", "{adj} {noun2}", "Beneath {place}", "The {noun} Below"],
  "adj": ["Hollow", "Pale", "Rotting", "Whispering", "Black", "Cold", "Hungry", "Forgotten", "Crawling", "Silent"],
  "noun": ["House", "Basement", "Well", "Attic", "Fog", "Mirror", "Cellar", "Woods", "Static", "Hollow", "Bell", "Stair"],
  "noun2": ["Dark", "Walls", "Teeth", "Echoes", "Roots"],
  "place": ["Black Hollow", "the Marlowe House", "Grimsby Pines", "the old sanatorium", "Hollow Creek", "the derelict mill"],
  "obj": ["the black box", "the old tape", "the nursery rhyme", "the locked room", "the photograph that changed"],
  "foe": ["the thing in the walls", "the hollow man", "the whisperer", "whatever wore his face"],
  "verb": ["Waits", "Breathes", "Watches", "Hungers", "Remembers"],
  "extra": [
    "The {house|woods|basement} was {quiet|too quiet|breathing|wrong} in a way {hero} could not name.",
    "{hero} {heard|felt|saw} it again at {3 a.m.|dusk|midnight}: {scratching|whispering|footsteps|nothing at all}.",
    "The {lights|radio|phone} {died|flickered|lied}, and {ally} stopped {laughing|talking|pretending}.",
    "Something had been in the {room|attic|cellar}, and it had left the {door|window|mirror} {open|wrong|watching}.",
    "{hero} told {him_her}self it was the {wind|house settling|imagination}. It was not.",
    "The {obj} should never have been {opened|played|read|found}.",
    "In {place}, the {dark|fog|silence} had {teeth|eyes|patience|a name}.",
  ]},
}

FICTION_CHAPTER_NAMES = {
 "sf": ["Launch Window", "The Long Dark", "Signal Lost", "New Ceres", "The Core", "Rogue Vector", "Event Horizon", "The Choice", "Burn", "Home Signal", "Epilogue: Static"],
 "fantasy": ["The Oath", "Into the Wild", "The Old Road", "Shadows Gather", "The Price", "The Turning", "The Last Stand", "The Crown", "Ashes", "The Road Home", "Epilogue: Song"],
 "mystery": ["The Client", "The Scene", "Persons of Interest", "The Alibi", "The Missing Piece", "A Dark Turn", "The Trap", "The Confrontation", "The Truth", "Aftermath", "Epilogue: Filed Away"],
 "romance": ["First Glance", "The Awkward Middle", "Small Mercies", "The Misunderstanding", "Distance", "The Letter", "The Return", "Saying It", "The Dance", "Epilogue: Years Later"],
 "horror": ["The Move", "First Night", "The Sounds", "The History", "It Knows", "The Basement", "No Signal", "The Truth", "The Last Night", "Epilogue: Quiet"],
}

# ---------------------------------------------------------------- fiction builder

def _strip_the(s):
    return s[4:] if s.lower().startswith("the ") else s

# ---------------------------------------------------------------- sources
# The progress loop: the source slot cycles the six network sources
# (specs, wiki, leaks, patents, telephone-book AIs, mall products) plus one
# standalone original. No source starves; new catalog records automatically
# become eligible book seeds on the next drip run.
SOURCE_CYCLE = ["spec", "wiki", "leaks", "patent", "ai", "mall", "original"]

def source_for(i):
    return SOURCE_CYCLE[(i - 1) % len(SOURCE_CYCLE)]

def lineage_for(kind, rec):
    sid, title, blurb, url = rec
    short = title if len(title) <= 90 else title[:87] + "..."
    labels = {
        "spec": f"Based on {sid}",
        "wiki": f"Based on JAH Wiki article ({sid})",
        "leaks": f"Based on dossier {sid}",
        "patent": f"Based on patent {sid}",
        "ai": f"Based on AI {title} ({sid})",
        "mall": f"Based on mall product {title} ({sid})",
    }
    return {"kind": kind, "id": sid, "label": labels[kind], "url": url,
            "title": short, "blurb": blurb[:240] if blurb else ""}

def build_fiction(g, idx, gkey, bank, rec=None, lin=None):
    hero, ally = unique_names(g, 2)
    foe_name = person_name(g)
    home = g.pick(bank["place"]); dest = g.pick([p for p in bank["place"] if p != home])
    obj = _strip_the(g.pick(bank["obj"])); foe = _strip_the(g.pick(bank["foe"]))
    rterms = rec_terms(rec[1], 6) if rec else []
    if rterms:
        # the tale's central object grows out of the source record's language
        obj = f"{rterms[0]} {g.pick(bank['noun']).lower()}"
        if len(rterms) > 1 and g.num(0, 1):
            obj = f"{rterms[0]} {rterms[1]} {g.pick(bank['noun']).lower()}"
    season = g.pick(["spring", "summer", "autumn", "winter"])
    elder = g.pick(["elder", "keeper", "stranger", "captain", "librarian", "innkeeper"])
    ctx = {"hero": hero, "ally": ally, "foe": foe, "foe_name": foe_name,
           "home": home, "dest": dest, "obj": obj, "season": season,
           "elder": elder, "his_her": "his" if g.num(0, 1) else "her",
           "he_she": "he" if g.num(0, 1) else "she",
           "he_she2": "he" if g.num(0, 1) else "she",
           "him_her": "him" if g.num(0, 1) else "her",
           "clue": g.pick(["clue", "detail", "discrepancy", "thread"]),
           "room": g.pick(["room", "study", "office", "parlor"]),
           "news": g.pick(["news", "word", "a warning", "a map"])}
    ctx.update({k: g.pick(v) for k, v in bank.items()
                if k not in ("title", "extra") and isinstance(v, list) and k not in ctx})
    ctx["noun2"] = g.pick(bank.get("noun2", bank["noun"]))
    ctx["verb"] = g.pick(bank.get("verb", ["stood", "waited"]))

    # title
    tctx = dict(ctx); tctx["adj"] = g.pick(bank["adj"]); tctx["noun"] = g.pick(bank["noun"])
    if rterms and g.num(0, 1):
        tctx["adj"] = rterms[0].title()
        if len(rterms) > 2:
            tctx["noun"] = rterms[1].title() + " " + g.pick(bank["noun"])
    title = fill(g, g.pick(bank["title"]), tctx).title()
    title = title.replace("'S ", "'s ")

    ch_names = FICTION_CHAPTER_NAMES[gkey]
    n_ch = g.num(8, 11)
    chapters = []
    beats = ["open", "world", "world", "rise", "rise", "rise", "twist",
             "climax", "climax", "close", "close"][:n_ch]
    bank_all = CORE_SENT + bank["extra"]
    used = set()
    for ci in range(n_ch):
        cname = ch_names[ci] if ci < len(ch_names) else f"Chapter {ci+1}"
        n_para = g.num(3, 5)
        paras = []
        for _ in range(n_para):
            n_sent = g.num(3, 6)
            cands = g.shuffled(bank_all)
            sents, si = [], 0
            while len(sents) < n_sent and si < len(cands):
                key = cands[si]; si += 1
                s = fill(g, key, ctx)
                if s not in used or g.num(0, 3) == 0:
                    used.add(s); sents.append(s)
            if ci == n_ch - 1 and not paras:
                pass
            if beat_has_dialog := (g.num(0, 4) == 0 and len(sents) > 1):
                pos = g.num(1, len(sents) - 1)
                sents.insert(pos, fill(g, g.pick(CORE_DIALOG), ctx))
            paras.append(" ".join(sents))
        chapters.append({"t": cname, "b": "\n\n".join(paras)})

    insp = f" Inspired by {lin['label']}." if lin else ""
    desc = " ".join([
        fill(g, g.pick([
            "{hero} never meant to {leave|find|carry|chase} the {obj} — but some {stories|roads|objects} choose their people.",
            "When the {obj} {surfaces|goes missing|calls out}, {hero} must {leave|flee|return to} {home} and face the {foe}.",
            "A {adj2} tale of {theme}: {hero} and {ally} {journey|race|stumble} toward {dest}, where the {obj} will decide everything.",
        ]), {**ctx, "adj2": g.pick(["gripping", "sweeping", "quiet", "haunting", "bold"]),
              "theme": g.pick(["courage", "loyalty", "sacrifice", "hope", "redemption", "discovery"])}),
        fill(g, g.pick([
            "Book {num} in the Signature {gname} collection — a complete original novel.",
            "A finished Signature novel: {nch} chapters, full text, ready to read aloud.",
        ]), {**ctx, "num": idx, "gname": GNAME[gkey], "nch": n_ch}),
    ]) + insp
    if lin:
        chapters.append({"t": "Source Note",
            "b": (f"This is an original generated tale inspired by {lin['label']}: "
                  f"\u201c{lin['title']}\u201d. The people, places, and events in "
                  f"this book are invented; the source record stands on its own. "
                  f"Find it in the Source Lineage section of this page.")})
    return title, desc, chapters

# ---------------------------------------------------------------- textbook banks

SUBJECTS = {
 "math": {
  "topics": ["Fractions & Decimals", "Algebra Foundations", "Geometry & Shapes",
             "Ratios & Proportions", "Probability Basics", "Intro to Calculus",
             "Number Theory", "Measurement & Units"],
  "terms": {
   "Fractions & Decimals": [("fraction", "a part of a whole, written as one number over another"),
     ("decimal", "a way of writing fractions with a decimal point"),
     ("equivalent fractions", "different fractions that name the same amount")],
   "Algebra Foundations": [("variable", "a letter that stands for an unknown number"),
     ("equation", "a mathematical sentence stating two expressions are equal"),
     ("coefficient", "the number multiplied by a variable")],
   "Geometry & Shapes": [("perimeter", "the total distance around a shape"),
     ("area", "the amount of surface a shape covers"),
     ("angle", "the measure of turn between two lines")],
   "Ratios & Proportions": [("ratio", "a comparison of two quantities"),
     ("proportion", "an equation stating two ratios are equal"),
     ("unit rate", "a ratio comparing a quantity to one unit of another")],
   "Probability Basics": [("probability", "a number from 0 to 1 measuring how likely an event is"),
     ("outcome", "a possible result of an experiment"),
     ("sample space", "the set of all possible outcomes")],
   "Intro to Calculus": [("derivative", "the rate at which a function changes"),
     ("limit", "the value a function approaches as input nears some point"),
     ("integral", "the accumulation of quantities, such as area under a curve")],
   "Number Theory": [("prime number", "a whole number greater than 1 with exactly two divisors"),
     ("factor", "a number that divides another evenly"),
     ("multiple", "the product of a number and an integer")],
   "Measurement & Units": [("unit", "a standard quantity used for measuring"),
     ("conversion", "changing a measurement from one unit to another"),
     ("precision", "how exact a measurement is")],
  },
  "example": [
    "A rectangle is {a} cm wide and {b} cm tall. Its area is {a} x {b} = {ab} square centimeters.",
    "Maya has {a} apples and gives away {b}. She has {a} - {b} = {amb} apples left.",
    "A recipe calls for {a} cups of flour. Tripling it needs {a} x 3 = {a3} cups.",
    "A bag holds {a} red and {b} blue marbles, {ab} total. The chance of drawing red is {a} out of {ab}.",
    "Solve for x: x + {a} = {ab}. Subtracting {a} from both sides gives x = {b}.",
    "A car drives {a} km in {b} hours, a speed of {a}/{b} = {div} km/h.",
  ]},
 "physics": {
  "topics": ["Motion & Speed", "Forces & Newton's Laws", "Energy & Work",
             "Waves & Sound", "Electricity Basics", "Light & Optics",
             "Gravity & Orbits", "Heat & Temperature"],
  "terms": {
   "Motion & Speed": [("speed", "distance traveled divided by time"),
     ("velocity", "speed in a stated direction"),
     ("acceleration", "the rate of change of velocity")],
   "Forces & Newton's Laws": [("force", "a push or pull, measured in newtons"),
     ("inertia", "the tendency of objects to resist changes in motion"),
     ("friction", "a force that opposes sliding motion")],
   "Energy & Work": [("energy", "the capacity to do work"),
     ("kinetic energy", "energy of motion"),
     ("potential energy", "stored energy due to position")],
   "Waves & Sound": [("wavelength", "the distance between repeating wave peaks"),
     ("frequency", "how many wave cycles pass per second"),
     ("amplitude", "the height of a wave, tied to its energy")],
   "Electricity Basics": [("current", "the flow of electric charge"),
     ("voltage", "the push that drives current"),
     ("resistance", "opposition to current flow")],
   "Light & Optics": [("reflection", "light bouncing off a surface"),
     ("refraction", "light bending as it enters a new medium"),
     ("spectrum", "the rainbow of colors in white light")],
   "Gravity & Orbits": [("gravity", "the attraction between masses"),
     ("orbit", "a curved path around a larger body"),
     ("weight", "the force of gravity on a mass")],
   "Heat & Temperature": [("temperature", "a measure of average particle motion"),
     ("conduction", "heat moving through direct contact"),
     ("convection", "heat moving through flowing fluids")],
  },
  "example": [
    "A runner covers {a} meters in {b} seconds: speed = {a}/{b} = {div} m/s.",
    "A {a} kg cart pushed with {b} N accelerates at {b}/{a} = {div2} m/s^2 (F = ma).",
    "Lifting a {a} kg box {b} meters does {a} x 9.8 x {b} = {w} joules of work.",
    "A wave with frequency {a} Hz and wavelength {b} m travels at {a} x {b} = {ab} m/s.",
    "A circuit with {a} V across {b} ohms carries {a}/{b} = {div} amps (Ohm's law).",
  ]},
 "chemistry": {
  "topics": ["Atoms & Elements", "The Periodic Table", "Chemical Bonds",
             "Reactions & Equations", "Acids & Bases", "States of Matter",
             "Solutions & Mixtures", "Intro to Organic Chemistry"],
  "terms": {
   "Atoms & Elements": [("atom", "the smallest unit of ordinary matter"),
     ("element", "a pure substance of one kind of atom"),
     ("isotope", "atoms of one element with different neutron counts")],
   "The Periodic Table": [("period", "a horizontal row of the periodic table"),
     ("group", "a vertical column sharing chemical traits"),
     ("metal", "an element that conducts heat and electricity")],
   "Chemical Bonds": [("ionic bond", "a bond formed by electron transfer"),
     ("covalent bond", "a bond formed by electron sharing"),
     ("molecule", "two or more atoms joined by bonds")],
   "Reactions & Equations": [("reactant", "a starting substance in a reaction"),
     ("product", "a substance formed by a reaction"),
     ("catalyst", "a substance that speeds a reaction without being consumed")],
   "Acids & Bases": [("acid", "a substance releasing hydrogen ions in water"),
     ("base", "a substance accepting hydrogen ions"),
     ("pH", "a 0-14 scale measuring acidity")],
   "States of Matter": [("solid", "matter with fixed shape and volume"),
     ("evaporation", "liquid turning to gas at the surface"),
     ("plasma", "ionized gas, the state of stars")],
   "Solutions & Mixtures": [("solution", "a uniform mixture of solute and solvent"),
     ("solubility", "how much solute dissolves in a solvent"),
     ("concentration", "the amount of solute per unit of solution")],
   "Intro to Organic Chemistry": [("hydrocarbon", "a compound of hydrogen and carbon"),
     ("polymer", "a long chain of repeating units"),
     ("functional group", "an atom group giving a molecule its reactivity")],
  },
  "example": [
    "Water forms when {a} hydrogen atoms join {b} oxygen atom: {a}H + {b}O -> H{a}O{b}, balanced as 2H2 + O2 -> 2H2O.",
    "Table salt's formula unit NaCl has molar mass about 23 + 35.5 = 58.5 g/mol.",
    "Mixing {a} g of salt into {b} g of water makes a solution of about {pct}% concentration.",
    "Vinegar (pH ~3) is {diff} times more acidic than pure water (pH 7).",
  ]},
 "biology": {
  "topics": ["Cells & Organelles", "Genetics & DNA", "Evolution & Natural Selection",
             "Ecology & Ecosystems", "Human Body Systems", "Plants & Photosynthesis",
             "Classification of Life", "Microbes & Disease"],
  "terms": {
   "Cells & Organelles": [("cell", "the basic unit of life"),
     ("nucleus", "the organelle holding a cell's DNA"),
     ("mitochondrion", "the organelle that releases energy from food")],
   "Genetics & DNA": [("gene", "a DNA section coding for a trait"),
     ("chromosome", "a packaged DNA molecule"),
     ("mutation", "a change in a DNA sequence")],
   "Evolution & Natural Selection": [("natural selection", "differential survival favoring helpful traits"),
     ("adaptation", "a trait improving survival"),
     ("fossil", "preserved remains of ancient life")],
   "Ecology & Ecosystems": [("ecosystem", "a community plus its environment"),
     ("producer", "an organism making its own food"),
     ("food web", "linked feeding relationships")],
   "Human Body Systems": [("neuron", "a nerve cell carrying signals"),
     ("antibody", "a protein that targets invaders"),
     ("homeostasis", "the body's stable internal balance")],
   "Plants & Photosynthesis": [("photosynthesis", "plants converting light to sugar"),
     ("chlorophyll", "the green pigment capturing light"),
     ("stoma", "a leaf pore controlling gas exchange")],
   "Classification of Life": [("species", "organisms that can interbreed"),
     ("genus", "a group of closely related species"),
     ("taxonomy", "the science of naming organisms")],
   "Microbes & Disease": [("bacterium", "a single-celled microbe"),
     ("virus", "an infectious particle needing a host cell"),
     ("vaccine", "a preparation training immunity")],
  },
  "example": [
    "A human body has about {a} trillion cells working together as one organism.",
    "If two carriers of a recessive trait have children, about 1 in {b} shows the trait.",
    "A forest of {a} hectares can hold roughly {a} x 400 = {a400} trees.",
    "The human heart beats about {a} times per day: {a} x 60 x 24 / 1000 = {k} thousand beats.",
  ]},
 "history": {
  "topics": ["Ancient Civilizations", "The Middle Ages", "The Age of Exploration",
             "Revolutions & Independence", "The Industrial Era", "The Modern World",
             "History Study Skills", "Primary Sources & Evidence"],
  "terms": {
   "Ancient Civilizations": [("civilization", "a complex society with cities and writing"),
     ("empire", "a large territory under one ruler"),
     ("artifact", "an object made by past people")],
   "The Middle Ages": [("feudalism", "a system of lords, vassals, and land"),
     ("manor", "a lord's estate and village"),
     ("guild", "an association of craftspeople")],
   "The Age of Exploration": [("navigation", "planning and directing sea voyages"),
     ("colony", "a settlement under a distant power"),
     ("trade route", "a path used for commerce")],
   "Revolutions & Independence": [("revolution", "a fundamental political overturning"),
     ("declaration", "a formal public statement"),
     ("constitution", "a nation's fundamental law")],
   "The Industrial Era": [("industrialization", "the shift to machine manufacturing"),
     ("urbanization", "population movement into cities"),
     ("labor movement", "organized workers seeking better conditions")],
   "The Modern World": [("globalization", "growing worldwide interconnection"),
     ("cold war", "the 1947-1991 US-Soviet rivalry"),
     ("civil rights", "movements for equal legal rights")],
   "History Study Skills": [("chronology", "ordering events in time"),
     ("cause and effect", "linking actions to outcomes"),
     ("historiography", "the study of how history is written")],
   "Primary Sources & Evidence": [("primary source", "firsthand evidence from the time"),
     ("bias", "a slant shaping how evidence is presented"),
     ("corroboration", "checking claims against multiple sources")],
  },
  "example": [],
  "facts": [
    "In 1776, the American colonies declared independence from Britain.",
    "The printing press, spread by Gutenberg around 1440, made books widely affordable.",
    "Ancient Egypt built the Great Pyramid of Giza around 2560 BCE.",
    "The Roman Empire at its height (c. 117 CE) ringed the Mediterranean Sea.",
    "In 1492, Columbus reached the Americas, beginning sustained European contact.",
    "The steam engine's improvements by James Watt (1776) powered the Industrial Revolution.",
    "In 1969, Apollo 11 landed the first humans on the Moon.",
    "The fall of the Berlin Wall in 1989 marked the Cold War's end.",
    "Ancient Athens developed early democracy around the 5th century BCE.",
    "The Silk Road linked China to the Mediterranean for over a thousand years.",
    "In 1865, the American Civil War ended and slavery was abolished in the US.",
    "The Renaissance (14th-17th centuries) revived art, science, and learning in Europe.",
  ]},
 "cs": {
  "topics": ["How Computers Think", "Algorithms & Flowcharts", "Data Structures",
             "Programming Basics", "The Internet & Networks", "Databases",
             "Cybersecurity Basics", "AI & Machine Learning Intro"],
  "terms": {
   "How Computers Think": [("binary", "base-2 numbers using only 0 and 1"),
     ("bit", "a single binary digit"),
     ("CPU", "the chip executing program instructions")],
   "Algorithms & Flowcharts": [("algorithm", "a step-by-step problem procedure"),
     ("pseudocode", "plain-language algorithm sketch"),
     ("complexity", "how runtime grows with input size")],
   "Data Structures": [("array", "an ordered list of items"),
     ("stack", "a last-in-first-out structure"),
     ("queue", "a first-in-first-out structure")],
   "Programming Basics": [("variable", "a named storage slot"),
     ("loop", "repeated execution of code"),
     ("function", "a reusable named block of code")],
   "The Internet & Networks": [("packet", "a chunk of data sent over networks"),
     ("IP address", "a device's network identifier"),
     ("protocol", "rules for communication")],
   "Databases": [("record", "one row of stored data"),
     ("query", "a request for data"),
     ("index", "a structure speeding up lookups")],
   "Cybersecurity Basics": [("encryption", "scrambling data so only key-holders read it"),
     ("phishing", "fraudulent messages stealing credentials"),
     ("firewall", "a barrier filtering network traffic")],
   "AI & Machine Learning Intro": [("model", "a trained program making predictions"),
     ("training data", "examples a model learns from"),
     ("neural network", "layered units inspired by brains")],
  },
  "example": [],
  "code": [
    ("Add two numbers", "a = {a}\nb = {b}\nprint(a + b)  # prints {ab}"),
    ("Count to N", "for i in range(1, {a}+1):\n    print(i)"),
    ("Find the biggest", "nums = [{a}, {b}, {c}]\nprint(max(nums))  # prints {m}"),
  ]},
}

TEXTBOOK_TITLES = {
 "math": ["{topic}: A Signature Course", "Mastering {topic}", "The {topic} Handbook", "{topic} Step by Step", "Signature {topic}"],
 "physics": ["{topic}: A Signature Course", "Understanding {topic}", "The {topic} Guide", "{topic} in Action"],
 "chemistry": ["{topic}: A Signature Course", "The World of {topic}", "{topic} Explained", "Practical {topic}"],
 "biology": ["{topic}: A Signature Course", "The Living World: {topic}", "{topic} Uncovered"],
 "history": ["{topic}: A Signature Course", "The Story of {topic}", "{topic}: People and Events", "Windows on {topic}"],
 "cs": ["{topic}: A Signature Course", "Code & Concepts: {topic}", "The {topic} Primer", "{topic} for Builders"],
}

TB_DEF_T = [
    "In {subject}, **{term}** means {defn}.",
    "{term_cap} — {defn}. This idea returns in every chapter, so keep it close.",
    "Key vocabulary: **{term}** ({defn}).",
]
TB_IDEA_T = [
    "The big idea: {idea}.",
    "What matters most here is {idea}.",
    "If you remember one thing, remember this: {idea}.",
]
TB_TRY_T = [
    "Try it: {task}",
    "Your turn: {task}",
    "Practice: {task}",
]
TB_NOTE_T = [
    "Common mistake: {note}",
    "Watch out: {note}",
    "Study tip: {note}",
]

# ---------------------------------------------------------------- textbook builder

def _numctx(g, a=2, b=12):
    x, y = g.num(a, b), g.num(a, b)
    z = g.num(a, b)
    ctx = {"a": x, "b": y, "c": z, "ab": x * y, "amb": x - y,
           "a3": x * 3, "a400": x * 400, "k": x * 60 * 24 // 1000,
           "div": round(x / y, 2) if y else 0, "m": max(x, y, z)}
    import math as _m
    ctx["w"] = round(x * 9.8 * y, 1)
    ctx["div2"] = round(y / x, 2) if x else 0
    ctx["pct"] = round(100 * x / (x + y), 1)
    ctx["diff"] = 10 ** 4
    return ctx

def build_textbook(g, idx, gkey, subj, rec=None, lin=None):
    topics = g.sample(subj["topics"], 3)
    title = fill(g, g.pick(TEXTBOOK_TITLES[gkey]),
                 {"topic": topics[0]}).replace("  ", " ")
    chapters = []
    for ti, topic in enumerate(topics):
        terms = subj["terms"][topic]
        for depth, cname in ((0, f"{topic}: Foundations"),
                             (1, f"{topic}: Going Deeper")):
            blocks = []
            # definition blocks (3 terms)
            t_defs = g.sample(terms, min(3, len(terms)))
            for term, defn in t_defs:
                blocks.append(fill(g, g.pick(TB_DEF_T),
                    {"subject": GNAME[gkey].lower(), "term": term,
                     "term_cap": term.capitalize(), "defn": defn}))
            # two big ideas
            for _ in range(2):
                idea = g.pick([
                    f"{t_defs[0][0]} connects directly to {terms[-1][0]}",
                    "small examples reveal the general rule",
                    "each new idea builds on the last one",
                    "patterns matter more than memorized facts",
                    f"experts in {topic.lower()} return to {t_defs[-1][0]} again and again",
                    "the vocabulary is the doorway; walk through it slowly",
                ])
                blocks.append(fill(g, g.pick(TB_IDEA_T), {"idea": idea}))
            # worked examples with REAL computed numbers (two when available)
            n_ex = 2 if subj.get("example") else 0
            for _ in range(n_ex):
                ex = fill(g, g.pick(subj["example"]), _numctx(g))
                blocks.append("Worked example: " + ex)
            if gkey == "history" and subj.get("facts"):
                blocks.append("Timeline note: " + g.pick(subj["facts"]))
                blocks.append("Timeline note: " + g.pick(subj["facts"]))
            if gkey == "cs" and subj.get("code"):
                for _ in range(2):
                    cname2, code = g.pick(subj["code"])
                    code = code.format(**_numctx(g))
                    blocks.append(f"Code sketch — {cname2}:\n{code}")
                blocks.append("Run each sketch mentally, line by line, before moving on.")
            # two try-it tasks
            for _ in range(2):
                task = g.pick([
                    f"explain {t_defs[0][0]} in your own words",
                    f"find two everyday examples of {terms[-1][0]}",
                    f"teach {t_defs[0][0]} to a friend in one minute",
                    f"draw and label a diagram of {t_defs[0][0]}",
                    f"write one question about {topic.lower()} you still have",
                    f"compare {t_defs[0][0]} and {terms[-1][0]} in two sentences",
                ])
                blocks.append(fill(g, g.pick(TB_TRY_T), {"task": task}))
            if depth == 1:
                blocks.append(fill(g, g.pick(TB_NOTE_T), {"note": g.pick([
                    "rushing past the vocabulary — learn the words first",
                    "memorizing steps without understanding the why",
                    "skipping the worked examples",
                    "confusing similar-sounding terms — compare them side by side",
                ])}))
                blocks.append("Chapter summary: " + " ".join(g.sample([
                    f"{topic} builds on {topics[0]}.",
                    f"The key terms this chapter were {t_defs[0][0]} and {terms[-1][0]}.",
                    "Review the worked example before moving on.",
                    "The practice tasks lock in the ideas.",
                    f"Next, {topic} meets the real world in the chapters ahead.",
                ], 3)))
            else:
                blocks.append(f"Link forward: everything in this chapter prepares you for "
                              f"{topic}: Going Deeper, where the same ideas get sharper.")
            chapters.append({"t": cname, "b": "\n\n".join(blocks)})
    desc = (f"A complete Signature {GNAME[gkey]} textbook covering "
            f"{', '.join(topics)} — definitions, worked examples with real "
            f"computed answers, practice tasks, and study notes. "
            f"{len(chapters)} chapters of original instructional text.")
    if lin:
        rs = rec_short(rec[1], 8)
        case = [
            f"Real record on the shelf: {lin['label']} — \u201c{lin['title']}\u201d.",
        ]
        if lin.get("blurb"):
            case.append(f"The catalog describes it this way: {lin['blurb']}")
        t0, d0 = subj["terms"][topics[0]][0][0], subj["terms"][topics[0]][0][1]
        case += [
            f"Through this book's lens, the record is {t0} at work ({d0}).",
            f"Ask yourself: which idea from {topics[0]} explains {rs} best — and which idea does it challenge?",
            "Write your answer in two paragraphs, then check it against the chapter summaries.",
            "You can open the source record itself from this book's Source Lineage section.",
        ]
        chapters.append({"t": f"Case Study: {rs}", "b": "\n\n".join(case)})
        desc += f" Includes a case study drawn from {lin['label']}."
    return title, desc, chapters

# ---------------------------------------------------------------- children's builder

CHILD_HEROES = ["Pip the rabbit", "Moss the turtle", "Wren the sparrow",
    "Bramble the hedgehog", "Tansy the mouse", "Fenn the fox kit",
    "Lark the lamb", "Nixie the newt", "Sorrel the squirrel",
    "Puddle the duckling", "Clover the calf", "Thistle the kitten"]
CHILD_PLACES = ["the whispering meadow", "the blueberry hill", "the old oak hollow",
    "the giggling brook", "the sunflower field", "the mossy stone bridge",
    "the firefly clearing", "the sleepy pond", "the berry bramble",
    "the tall-grass sea"]
CHILD_LESSONS = ["sharing makes joy grow", "brave means trying anyway",
    "kind words are magic", "mistakes help us learn",
    "friends come in all sizes", "patience brings sweet berries",
    "asking for help is strong", "everyone has a special gift"]

CHILD_SENT = [
    "{hero} woke up {bright-eyed|wiggly|stretchy|smiley} on a {sunny|breezy|dewy|sparkly} morning.",
    "Today was the day {hero} would visit {place}.",
    "{friend} was already there, {hopping|skipping|twirling|giggling}.",
    '"{greet}!" called {friend}. "{hero}, you came!"',
    "Together they {played|explored|counted clouds|picked berries}.",
    "{hero} found {a shiny pebble|a curly leaf|a feather|a round acorn} and showed {friend}.",
    '"{mine|Look|Wow}!" said {hero}. "It is {beautiful|funny|soft|perfect}!"',
    "Then came a {little|tiny|small} problem: {problem}.",
    "{hero} felt {wobbly|sad|stuck|worried} for a moment.",
    '"{encourage}," said {friend}, and {hero} took a deep breath.',
    "They {tried again|thought together|asked kindly|shared the load}.",
    "And guess what? It {worked|was fun|felt better|made them laugh}!",
    "The sun {smiled|peeked|glowed}, and the {birds|bees|leaves} {sang|buzzed|danced}.",
    "That evening, {hero} learned that {lesson}.",
    "{hero} {yawned|snuggled|smiled} and dreamed of {place}.",
]

def build_children(g, idx, rec=None, lin=None):
    hero = g.pick(CHILD_HEROES)
    friend = g.pick([h for h in CHILD_HEROES if h != hero])
    place = g.pick(CHILD_PLACES)
    lesson = g.pick(CHILD_LESSONS)
    ctx = {"hero": hero, "friend": friend, "place": place, "lesson": lesson,
           "greet": g.pick(["Hooray", "Hello", "Yippee", "Good morning"]),
           "problem": g.pick(["the bridge was wobbly", "the berries were too high",
                              "the map was upside down", "the kite was tangled",
                              "the picnic basket was heavy", "the path split in two"]),
           "encourage": g.pick(["You can do it", "Try with me", "One step at a time", "I believe in you"]),
           "mine": g.pick(["Look", "Wow", "Oh"])}
    title = fill(g, g.pick([
        "{hero} and the {thing}", "The {adj} Day of {hero}", "{hero}'s Big {thing}",
        "{hero} Goes to {place2}", "A {thing} for {hero}", "{hero} Learns to {verb}",
    ]), {**ctx, "thing": g.pick(["Picnic", "Adventure", "Surprise", "Parade", "Treasure", "Song"]),
        "adj": g.pick(["Sunny", "Breezy", "Happy", "Wiggly", "Sparkly"]),
        "place2": g.pick(["Blueberry Hill", "the Meadow", "Sunflower Field", "the Pond"]),
        "verb": g.pick(["Share", "Fly", "Swim", "Dance", "Sing"])})
    n_ch = g.num(6, 8)
    ch_names = ["Morning", "The Walk", "A Friend", "The Little Problem",
                "Trying Again", "The Happy Fix", "Snack Time", "Bedtime"][:n_ch]
    chapters = []
    for ci in range(n_ch):
        sents = [fill(g, s, ctx) for s in g.sample(CHILD_SENT, g.num(7, 10))]
        chapters.append({"t": ch_names[ci], "b": " ".join(sents)})
    desc = (f"A complete read-aloud children's story starring {hero}. "
            f"{n_ch} short chapters about friendship and {lesson}. "
            "Gentle, original, and made for bedtime.")
    if lin:
        chapters[-1]["b"] += (f"\n\nGrown-up note: this story was inspired by "
                              f"{lin['label']}. The tale itself is invented.")
        desc += f" Inspired by {lin['label']}."
    return title, desc, chapters

# ---------------------------------------------------------------- poetry builder

POEM_THEMES = {
 "dawn": ["light", "morning", "gold", "waking", "birdsong", "dew", "horizon", "new"],
 "sea": ["waves", "tide", "salt", "deep", "shell", "foam", "moon-pull", "voyage"],
 "stars": ["night", "constellation", "silver", "dream", "orbit", "quiet", "watcher", "far"],
 "garden": ["petal", "root", "bee", "soil", "bloom", "rain", "green", "seed"],
 "rain": ["cloud", "puddle", "thunder", "grey", "drum", "wet", "storm", "wash"],
 "journey": ["road", "dust", "mile", "pack", "horizon", "step", "wind", "home"],
}
POEM_LINES = [
    "I {walked|watched|waited} where the {w1} meets the {w2},",
    "and {w3} fell soft as {w4} on my hands.",
    "The {w5} remembers every {w6} we {kept|lost|named|found},",
    "while {w7} keeps its {w8} {far|near|secret|bright}.",
    "{w1_cap} rises, {w2} answers, {w3} {sings|stays|sleeps|returns},",
    "I carry {w4} like a {lamp|song|stone|promise} through the {w5}.",
    "O {w6}, O {w7}, {teach|tell|lend|leave} me your {w8},",
    "before the {w1} forgets the {w2} again.",
    "We {planted|painted|counted|followed} {w3} in rows of {w4},",
    "and the {w5} gave back {w6} a hundredfold.",
    "Small {w7}, bright {w8}, {do not|never} {fade|fear|leave},",
    "the {w1} is {wider|kinder|older} than we knew.",
    "Here is my {w2}: {w3}, {w4}, and {w5},",
    "tied with {w6} and sealed with {w7}.",
    "The {w8} {turns|burns|learns|yearns} at the edge of {w1},",
    "and I am {part|proof|particle} of its {w2}.",
]
POEM_TITLES = ["{w1_cap} Song", "Ode to {w2}", "The {w3} Hour", "{w4} and {w5}",
               "Field Notes on {w6}", "What the {w7} Said", "Elegy for {w8}",
               "Hymn of {w1}", "Small Book of {w2}", "The {w3} {w4}"]

def build_poetry(g, idx, rec=None, lin=None):
    theme = g.pick(list(POEM_THEMES))
    words = POEM_THEMES[theme]
    rterms = rec_terms(rec[1], 8) if rec else []
    if len(rterms) >= 4:
        words = (rterms + words)[:8]
        theme = "the source record"
    n_poems = g.num(10, 14)
    chapters = []
    used_t = set()
    for _ in range(n_poems):
        w = g.sample(words, 8)
        ctx = {f"w{i+1}": w[i] for i in range(8)}
        ctx["w1_cap"] = w[0].capitalize()
        t = fill(g, g.pick(POEM_TITLES), ctx)
        if t in used_t:
            t = f"{t} ({g.num(2,9)})"
        used_t.add(t)
        stanzas = []
        for _ in range(g.num(3, 5)):
            lines = [fill(g, ln, ctx) for ln in g.sample(POEM_LINES, 4)]
            stanzas.append("\n".join(lines))
        chapters.append({"t": t, "b": "\n\n".join(stanzas)})
    title = fill(g, g.pick([
        "{w1_cap} and Other Poems", "Collected {theme_cap} Verses",
        "The Signature {theme_cap} Book", "Poems of {w2} and {w3}",
        "{n} Small Poems",
    ]), {"w1_cap": words[0].capitalize(), "w2": words[1], "w3": words[2],
         "theme_cap": theme.capitalize(), "n": n_poems})
    desc = (f"A complete original poetry collection: {n_poems} poems on "
            f"{theme}, each in full. Written fresh for the Signature "
            "depository — no borrowed lines, no borrowed voices.")
    if lin:
        desc += f" Themed on {lin['label']}."
    return title, desc, chapters

# ---------------------------------------------------------------- technical manual builder

DEVICES = ["Home Assistant Hub", "Solar Lantern", "Water Purifier", "Garden Sensor",
    "Weather Station", "Air Quality Monitor", "Smart Kettle", "Bike Computer",
    "Seed Starter Kit", "Workshop Multitool", "Portable Charger", "Rain Barrel Pump"]
MANUAL_SECTIONS = ["Safety First", "What Is in the Box", "Setup in Six Steps",
    "Everyday Operation", "Care & Cleaning", "Troubleshooting",
    "Specifications", "Warranty & Support"]

def build_manual(g, idx, rec=None, lin=None):
    device = g.pick(DEVICES)
    model = f"SG-{g.num(100, 999)}"
    companion = ""
    if rec and lin and lin["kind"] in ("mall", "spec"):
        # a genuine owner's manual for the sourced product / invention
        device = rec_short(rec[1], 5).title() or device
        model = "".join(ch for ch in lin["id"] if ch.isdigit())[-6:] or model
        model = f"SG-{model}"
        companion = f" This manual accompanies {lin['label']}."
    D = {"device": device, "model": model}
    sec = {}
    sec["Safety First"] = "\n\n".join([
        f"Read every step before you plug in the {device} ({model}).",
        "Keep the unit dry, away from open flame, and out of reach of small children.",
        "Unplug before cleaning. Never open the sealed case — there are no user-serviceable parts inside.",
        "If the case is cracked or smells unusual, stop using the unit and contact support.",
        "Do not drop the unit or stack heavy objects on it; internal alignment matters.",
        "In a thunderstorm, unplug the unit until the storm passes.",
    ])
    sec["What Is in the Box"] = "\n\n".join([
        f"1 x {device} ({model})",
        "1 x quick-start card, 1 x power cable, 2 x mounting screws, 1 x warranty leaflet.",
        "Check that all parts are present. Missing parts are replaced free within 30 days.",
        "Keep the box for at least the warranty period — it is the safest way to transport the unit.",
    ])
    steps = g.shuffled([
        "Unbox the unit and remove all packaging.",
        "Place the unit on a flat, stable surface with airflow on all sides.",
        "Connect the power cable to the unit, then to a wall outlet.",
        "Wait for the status light to turn solid green (about 60 seconds).",
        "Press and hold the pair button for three seconds to enter setup mode.",
        "Follow the on-screen or voice prompts to finish configuration.",
    ])[:6]
    sec["Setup in Six Steps"] = "\n\n".join(f"Step {i+1}: {s}" for i, s in enumerate(steps))
    sec["Everyday Operation"] = "\n\n".join([
        f"Press the main button once to wake the {device}.",
        "A short press cycles modes; a long press (2 seconds) powers down.",
        "The status light is your guide: green means ready, amber means working, red means attention needed.",
        "For best results, run the unit's self-check weekly from the settings menu.",
        "Keep a simple log of anything unusual — it helps support help you faster.",
        "Avoid blocking the vents during operation; the unit cools itself through them.",
        "If you will not use the unit for a week, power it down fully rather than leaving it asleep.",
    ])
    sec["Care & Cleaning"] = "\n\n".join([
        "Wipe the outside with a soft, dry cloth. Never use solvents.",
        "Clean vents monthly with a soft brush so airflow stays clear.",
        "Store in a cool, dry place if unused for more than a month.",
        "Charge the internal cell to about half before long storage.",
        "Inspect the power cable yearly for nicks or kinks; replace a damaged cable at once.",
        "A yearly self-check report, saved with your records, keeps warranty claims smooth.",
    ])
    probs = g.sample([
        ("Unit will not power on", "Check the cable at both ends; try a different outlet."),
        ("Status light stays red", "Run the self-check; note the error code and contact support."),
        ("Weak performance", "Clean the vents and move the unit away from heat sources."),
        ("Setup mode will not start", "Hold the pair button a full three seconds; watch for the blinking light."),
        ("Strange odor", "Unplug immediately and contact support — do not reuse."),
    ], 4)
    sec["Troubleshooting"] = "\n\n".join(f"Problem: {p}\nFix: {f}" for p, f in probs)
    sec["Specifications"] = "\n\n".join([
        f"Model: {model} | Power: {g.num(5, 60)} W | Weight: {round(g.num(20, 400)/100, 2)} kg",
        f"Operating temperature: {g.num(-5, 10)} C to {g.num(35, 50)} C",
        f"Expected service life: {g.num(3, 10)} years with normal care",
        "In the box dimensions and full test data ship with the printed manual.",
    ])
    sec["Warranty & Support"] = "\n\n".join([
        "Two-year limited warranty covering defects in materials and workmanship.",
        "Support hours: weekdays 8am-8pm; expect a reply within one business day.",
        "Keep your proof of purchase — the warranty starts on the purchase date.",
    ])
    chapters = [{"t": s, "b": sec[s]} for s in MANUAL_SECTIONS]
    title = f"The {device} ({model}) Owner's Manual"
    desc = (f"The complete owner's manual for the Signature {device} ({model}): "
            "safety, setup, daily use, care, troubleshooting, and full "
            "specifications. A finished, practical technical document." + companion)
    if lin and not companion:
        chapters.append({"t": "Companion Record",
            "b": (f"This manual is a companion volume to {lin['label']}: "
                  f"\u201c{lin['title']}\u201d. The manual itself is an original "
                  f"generated document; the source record stands on its own — "
                  f"find it in Source Lineage.")})
    return title, desc, chapters

# ---------------------------------------------------------------- philosophy builder

PHIL_CONCEPTS = ["time", "the mind", "free will", "beauty", "justice",
    "knowledge", "consciousness", "morality", "truth", "happiness",
    "identity", "language", "art", "death", "freedom", "meaning"]
PHIL_VIEWS = ["the classic view", "the skeptic's view", "the modern view",
    "the practical view", "the mystic's view"]

def build_philosophy(g, idx, rec=None, lin=None):
    concept = g.pick(PHIL_CONCEPTS)
    views = g.sample(PHIL_VIEWS, 3)
    C = {"concept": concept}
    chapters = []
    intro_extra = (f" We will test our ideas against a real case along the way: "
                   f"{lin['label']}." if lin else "")
    chapters.append({"t": f"What Is {concept.capitalize()}?",
        "b": "\n\n".join([
            f"Everyone uses the word '{concept}', but few stop to ask what it means.",
            f"This book is a slow walk around {concept}: looking at it from several sides, "
            "testing each view, and leaving you with better questions than you started with.",
            f"We begin with the ordinary sense of '{concept}' — how the word works in daily life — "
            "because philosophy that cannot touch ordinary life is only decoration.",
        ]) + intro_extra})
    for vi, view in enumerate(views):
        chapters.append({"t": f"View {vi+1}: {view.title()}",
            "b": "\n\n".join([
                f"{view.title()} holds that {concept} is best understood through "
                f"{g.pick(['careful reasoning', 'lived experience', 'what it does for us', 'its history'])}.",
                "Its strongest argument: " + g.pick([
                    f"it explains the cases other views stumble on",
                    "it fits what we actually do and say",
                    "it survives the hardest objections",
                    f"it makes sense of our feelings about {concept}",
                ]) + ".",
                "Its hardest objection: " + g.pick([
                    f"it seems to miss something essential about {concept}",
                    "it proves too much — or too little",
                    "ordinary people find it hard to live by",
                    "it leans on an assumption it never defends",
                ]) + ".",
                f"Hold both the argument and the objection in mind. {concept} deserves that much patience.",
            ])})
    chapters.append({"t": "A Thought Experiment",
        "b": "\n\n".join([
            f"Imagine two worlds, identical except in one detail about {concept}.",
            "In the first world, the ordinary view is exactly right. In the second, the skeptic is right.",
            "Now ask: what would be different for the people living there? What would they do differently?",
            f"If nothing changes, perhaps the dispute about {concept} is only words. "
            "If everything changes, you have found what is really at stake.",
            "Thought experiments do not settle questions; they show you where the question lives.",
        ])})
    chapters.append({"t": "Where This Leaves Us",
        "b": "\n\n".join([
            f"We have circled {concept} from {len(views)} sides and found no single view without cost.",
            "That is not failure. Philosophy rarely ends with a trophy; it ends with clearer sight.",
            f"Carry these questions into your week and watch how {concept} shows up in small decisions.",
            "The unexamined idea is not worth much — but the examined one is worth everything.",
        ] + ([f"A last exercise: take {lin['label']} and ask which of the three views "
               f"it supports — then steelman the view it seems to refute."] if lin else []))})
    title = fill(g, g.pick([
        "On {concept_cap}: A Short Philosophy", "{concept_cap} and the Examined Life",
        "Thinking About {concept_cap}", "The Signature Book of {concept_cap}",
    ]), {**C, "concept_cap": concept.capitalize()})
    desc = (f"A complete original philosophy book on {concept}: the question, "
            f"three rival views with objections, a thought experiment, and an "
            "open conclusion. Written to be read slowly.")
    if lin:
        desc += f" Worked against the real case of {lin['label']}."
    return title, desc, chapters

# ---------------------------------------------------------------- business builder

BIZ_CHAPTERS = ["The Idea", "Know Your Customer", "The Numbers",
                "Build the Team", "Launch Day", "Grow", "The Long Game"]
BIZ_IDEAS = ["a neighborhood repair cafe", "a mobile car-detailing service",
    "a subscription soup club", "a kids' coding workshop", "a plant-sitting network",
    "a resume-writing studio", "a weekend farmers' stall", "a home-organizing service",
    "a bicycle tour company", "a handmade soap line"]

def build_business(g, idx, rec=None, lin=None):
    idea = g.pick(BIZ_IDEAS)
    C = {"idea": idea}
    bodies = {
     "The Idea": [
        f"Every business starts as a sentence. Yours: {idea}.",
        "Write the sentence down. Say it to ten people. Watch their faces — "
        "confusion means the idea needs sharpening, not abandoning.",
        "The Signature test: can a twelve-year-old repeat your idea back correctly? If yes, it is clear enough to build.",
        "Ideas are cheap; clarity is the actual product at this stage.",
     ],
     "Know Your Customer": [
        "Your customer is not 'everyone'. Name one real person with the problem you solve.",
        "Ask that person what they tried before, what it cost, and what frustrated them.",
        "Ten honest conversations beat a hundred guesses. Take notes; patterns will appear by conversation six.",
        f"For {idea}, the customer is probably closer than you think — start with your own street.",
     ],
     "The Numbers": [
        "Open the Three-Bucket Budget: bucket one is costs, bucket two is price, bucket three is profit.",
        "List every cost honestly, including your own hours at a fair rate.",
        "Price is not cost plus hope. Price is what the customer gladly pays, tested in small experiments.",
        "Know your break-even number by heart: how many sales per week keeps the lights on?",
     ],
     "Build the Team": [
        "Hire for character, train for skill. Skills are teachable; reliability is not.",
        "Your first three people set the culture forever. Choose slowly.",
        "Write down how decisions get made before the first disagreement, not after.",
        "Pay fairly and on time. Trust compounds like interest.",
     ],
     "Launch Day": [
        "Launch small, launch real. One street, one weekend, one offer.",
        "Tell everyone beforehand; a launch nobody hears about is a rehearsal.",
        "Measure three things only: how many came, how many bought, how many returned.",
        "Whatever breaks on launch day is a gift — it shows you the weak joint for free.",
     ] + ([f"Case on the shelf: {lin['label']} — \u201c{lin['title']}\u201d. "
            f"Study what its makers got right, and what you would do differently."] if lin else []),
     "Grow": [
        "Growth is the Signature Flywheel: happy customers bring friends, friends bring feedback, feedback improves the offer.",
        "Grow at the speed of quality. A reputation takes years to build and a week to spend.",
        "Add one channel at a time. Master it before opening another.",
        "Reinvest early profits into the thing customers mention most.",
     ],
     "The Long Game": [
        "Year one is survival, year three is systems, year ten is legacy.",
        "Write the owner's manual for your business as if you will hand it to a stranger.",
        "The long game is won by people who show up on ordinary Tuesdays.",
        f"{idea.capitalize()} can outlive its founder if it is built on principles, not personality.",
     ],
    }
    chapters = [{"t": t, "b": "\n\n".join(bodies[t])} for t in BIZ_CHAPTERS]
    title = fill(g, g.pick([
        "The {idea_cap} Playbook", "Build It: {idea_cap}", "The Small Business of {idea_cap}",
        "From Idea to Income: {idea_cap}",
    ]), {**C, "idea_cap": idea.capitalize()})
    desc = (f"A complete original small-business guide built around one idea — "
            f"{idea}: from clarity to customers, numbers, team, launch, growth, "
            "and the long game. Practical, plain-spoken, finished.")
    if lin:
        desc += f" With a launch-day case drawn from {lin['label']}."
    return title, desc, chapters

# ---------------------------------------------------------------- assembler

def make_book(idx, pools=None):
    gkey = genre_for(idx)
    skind = source_for(idx)
    g = G(SALT + idx)
    rec, lin = None, None
    if pools is not None and skind != "original":
        pool = pools.get(skind) or []
        if pool:
            rec = pool_pick(pool, skind, idx)
            lin = lineage_for(skind, rec)
    bank = GENRE_OVERLAY.get(gkey)
    if bank is not None:
        title, desc, chapters = build_fiction(g, idx, gkey, bank, rec, lin)
    elif gkey in SUBJECTS:
        title, desc, chapters = build_textbook(g, idx, gkey, SUBJECTS[gkey], rec, lin)
    elif gkey == "children":
        title, desc, chapters = build_children(g, idx, rec, lin)
    elif gkey == "poetry":
        title, desc, chapters = build_poetry(g, idx, rec, lin)
    elif gkey == "manual":
        title, desc, chapters = build_manual(g, idx, rec, lin)
    elif gkey == "philosophy":
        title, desc, chapters = build_philosophy(g, idx, rec, lin)
    elif gkey == "business":
        title, desc, chapters = build_business(g, idx, rec, lin)
    else:
        raise ValueError(gkey)
    # ---- trademark-safety guard (Manon's rule): reject-and-regenerate ----
    # Any trademarked term or thin knockoff ("Hairy Potter") that slipped in
    # via source-record terms, banks, or invented names is replaced with an
    # invented substitute. sanitize_book_text masks lineage citations first
    # ("Based on ...", "Case Study:" titles, record IDs) so attribution
    # links stay truthful. It only draws from g when a hit exists, so clean
    # books are byte-identical to before (determinism preserved).
    title = sanitize_book_text(title, g)[0]
    desc = sanitize_book_text(desc, g)[0]
    chapters = [{"t": sanitize_book_text(c["t"], g)[0],
                 "b": sanitize_book_text(c["b"], g)[0]} for c in chapters]
    words = sum(words_of(c["b"]) + words_of(c["t"]) for c in chapters)
    words += words_of(title) + words_of(desc)
    bid = f"JAH-BOOK-{idx:06d}"
    return {
        "id": bid, "title": title, "author": AUTHOR,
        "genre": GNAME[gkey], "gkey": gkey, "desc": desc,
        "words": words, "chapters": chapters, "note": GEN_NOTE,
        "sources": [lin] if lin else [], "origin": skind,
    }, gkey, skind

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
    return os.path.join(VOL, f"books-c{n:05d}.json.gz")

def idx_entry(rec):
    return {"id": rec["id"], "t": rec["title"], "a": rec["author"],
            "g": rec["genre"], "w": rec["words"], "d": rec["desc"],
            "o": rec.get("origin", "original"),
            "ch": [c["t"] for c in rec["chapters"]]}

def load_idx():
    p = os.path.join(IDX, "books.idx.json.gz")
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_idx(entries):
    p = os.path.join(IDX, "books.idx.json.gz")
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, separators=(",", ":"))

def write_api(total, words, per_genre, n_chunks, per_source=None):
    # api.json is THE authoritative manifest for the Book Depository catalog.
    # Every count on the homepage, every shelf, every genre total, and the
    # sitemap derive from this file. Never hard-code counts elsewhere.
    # genres: mutually exclusive — every book has exactly one genre, so
    #   sum(genres.values()) == total_books.
    # origins: mutually exclusive — every book carries exactly one origin slot
    #   (the seven-source round-robin cycle: spec/wiki/leaks/patent/ai/mall/
    #   original), so sum(origins.values()) == total_books. These are
    #   CUMULATIVE catalog counts, not a per-run mix. "original" means a
    #   standalone Signature-original book; the other six mean the book was
    #   derived from (seeded by) that network record type and carries a
    #   source-lineage link. They do NOT partition by subject matter.
    api = {
        "site": "The Signature Book Depository",
        "site_id": "signature-books",
        "total_books": total,
        "total_words": words,
        "genres": per_genre,
        "genre_counts_note": ("Mutually exclusive: every book has exactly one "
                              "genre; the genre counts sum to total_books."),
        "origins": per_source or {},
        "origin_counts_note": ("Mutually exclusive and cumulative: every book "
                               "carries exactly one origin slot from the "
                               "seven-source cycle (spec, wiki, leaks, patent, "
                               "ai, mall, original); the origin counts sum to "
                               "total_books. 'original' = standalone "
                               "Signature-original book; the other six = the "
                               "book was derived from that network record "
                               "type and carries a source-lineage link."),
        "chunks": n_chunks,
        "chunk_size": CHUNK,
        "march_goal": 1000000,
        "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "index": "data/index/books.idx.json.gz",
        "index_encoding": ("gzip archive (application/gzip), JSON array of "
                           "compact index entries; decoded client-side with "
                           "DecompressionStream. Field map: id,title=t,"
                           "author=a,genre=g,words=w,desc=d,origin=o,"
                           "chapter_titles=ch. Full records live in "
                           "data/volumes/books-cNNNNN.json.gz (100/chunk)."),
        "schema": "data/index/books-schema.json",
        "manifest": "data/index/books-manifest.json",
        "note": ("All books are original generated works by/for the Signature system. "
                 "Derived books carry source-lineage links to the network record that seeded them."),
    }
    with open(os.path.join(IDX, "api.json"), "w") as f:
        json.dump(api, f, ensure_ascii=False, indent=1)
    write_books_manifest(api)

def write_books_manifest(api):
    # books-manifest.json: the site-level manifest. Count fields are copied
    # from api.json (the count authority) at build time so they cannot drift.
    man = {
        "site_id": "signature-books",
        "site_name": "The Signature Book Depository",
        "site_version": "1.0",
        "network_site": "12 of 25",
        "total_books": api["total_books"],
        "total_words": api["total_words"],
        "genre_counts": api["genres"],
        "origin_counts": api["origins"],
        "chunk_count": api["chunks"],
        "chunk_size": api["chunk_size"],
        "march_goal": api["march_goal"],
        "book_schema_version": "JAH-BOOK-RECORD/1.0",
        "schema": "data/index/books-schema.json",
        "index": api["index"],
        "chunk_manifest": "data/index/chunks-manifest.json",
        "sitemap": "sitemap.xml",
        "counts_authority": "data/index/api.json",
        "record_status": ("PUBLISHED — the drip only writes finished books; "
                          "records are immutable (never regenerated); "
                          "state.json next_index never revisits an ID."),
        "license": ("Original generated works by/for the Signature system, "
                    "by Justin Addam Higgins. Free to read. Reuse rights per "
                    "book record: read/copy/download permitted; modification "
                    "and redistribution terms stated per record."),
        "provenance_policy": ("Derived books name the network record that "
                              "seeded them via source-lineage links. No "
                              "real-world authors, no borrowed text, no "
                              "trademarked characters, no fake ISBNs or "
                              "publishers."),
        "updated": api["updated"],
        "canonical_url": "https://justinahiggins614-cmyk.github.io/signature-books/",
    }
    with open(os.path.join(IDX, "books-manifest.json"), "w") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)

def write_sitemap(total):
    # Unified sitemap across all three wings (books + magazines + library).
    # Delegates to code/sitemap_all.py so every drip keeps every wing fresh.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "sitemap_all", os.path.join(HERE, "sitemap_all.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.write_sitemap()

def write_robots():
    with open(os.path.join(ROOT, "robots.txt"), "w") as f:
        f.write("User-agent: *\nAllow: /\n"
                "Sitemap: https://justinahiggins614-cmyk.github.io/signature-books/sitemap.xml\n")

def write_browse():
    # Static crawlable browse pages (shards + genre hubs) + incremental
    # plaintext summary fallbacks. Idempotent — safe to run every drip.
    from build_browse import main as _bb
    _bb()

def write_feed():
    # Standardized machine-readable catalog feed.
    from build_feed import build_feed as _bf
    _bf()

def run(n):
    os.makedirs(VOL, exist_ok=True)
    os.makedirs(IDX, exist_ok=True)
    print("building six-source pools...", flush=True)
    pools = build_pools()
    for k, p in pools.items():
        print(f"  pool {k}: {len(p)} records", flush=True)
    st = load_state()
    start = st["next_index"]
    end = start + n
    entries = load_idx()
    seen_titles = {e["t"] for e in entries}
    per_genre = {}
    per_source = {}
    for e in entries:
        per_genre[e["g"]] = per_genre.get(e["g"], 0) + 1
        # origins are cumulative: every book carries exactly one origin slot
        # (the seven-source round-robin), so these counts partition the catalog
        o = e.get("o", "original")
        per_source[o] = per_source.get(o, 0) + 1
    total_words = sum(e["w"] for e in entries)

    buf = []          # pending records for current chunk
    chunk_no = (start - 1) // CHUNK + 1
    # if the last existing chunk is partial, reload it so we fill it first
    last_partial = None
    if start > 1 and (start - 1) % CHUNK:
        p = chunk_path(chunk_no)
        if os.path.exists(p):
            with gzip.open(p, "rt", encoding="utf-8") as f:
                last_partial = json.load(f)

    def flush():
        nonlocal buf, chunk_no, last_partial
        if last_partial is not None:
            recs = last_partial + buf
            last_partial = None
        else:
            recs = buf
        with gzip.open(chunk_path(chunk_no), "wt", encoding="utf-8") as f:
            json.dump(recs, f, ensure_ascii=False, separators=(",", ":"))
        buf = []
        chunk_no += 1

    new_recs = 0
    for idx in range(start, end):
        rec, gkey, skind = make_book(idx, pools)
        # title uniqueness guard (deterministic)
        t = rec["title"]
        if t in seen_titles:
            t = f"{t} (Vol. {idx})"
            rec["title"] = t
        seen_titles.add(t)
        buf.append(rec)
        entries.append(idx_entry(rec))
        per_genre[rec["genre"]] = per_genre.get(rec["genre"], 0) + 1
        per_source[skind] = per_source.get(skind, 0) + 1
        total_words += rec["words"]
        new_recs += 1
        if len(buf) + (len(last_partial) if last_partial else 0) >= CHUNK or \
           ((start - 1 + new_recs) % CHUNK == 0):
            flush()
        if new_recs % 500 == 0:
            print(f"  ... {new_recs}/{n} books", flush=True)
    if buf or last_partial is not None:
        flush()

    n_chunks = (end - 1 - 1) // CHUNK + 1 if end > 1 else 0
    save_idx(entries)
    write_api(end - 1, total_words, per_genre, n_chunks, per_source)
    write_sitemap(end - 1)
    write_browse()
    write_feed()
    write_robots()
    st["next_index"] = end
    save_state(st)
    print(f"done: books {start}..{end-1} ({new_recs} new), total {end-1}, "
          f"words {total_words}, chunks {n_chunks}")
    print("source mix this run:", per_source)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    a = ap.parse_args()
    run(a.n)

if __name__ == "__main__":
    main()
