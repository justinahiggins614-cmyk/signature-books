#!/usr/bin/env python3
"""Trademark-safety guard for the Signature Book Depository.

Manon's rule: every publishable book/text type is covered, including Signature
versions of themes — but never real trademarked names (Harry Potter, not
"Hairy Potter" knockoffs either).

Provides:
  TM_PHRASES / TM_WORDS  - curated blocklist (famous franchises, studios, brands,
                            characters, products). Matched case-insensitively.
  tm_hits(text)           - exact matches -> list of (kind, matched_text)
  is_tm_clean(text)       - True when no exact or fuzzy hit
  fuzzy_hits(text)        - near-misspellings (edit distance <= 2 via SymSpell
                            delete-variant index) -> list of (token, block_term)
  sanitize_text(text, g)  - replace every violating span with an invented,
                            deterministic substitute drawn from g (a G rng).
                            Only consumes rng draws when a hit exists, so clean
                            text is byte-identical and generation stays
                            deterministic.

Integrated into code/drip_books.py make_book(): every new book is scanned and
auto-sanitized (reject-and-regenerate for titles, in-place substitution for
body text) before it is stored.
"""
import re
import os
from collections import defaultdict

# ---------------------------------------------------------------- blocklist
# Multi-word phrases / distinctive marks (matched case-insensitively).
TM_PHRASES = [
    "harry potter", "star wars", "star trek", "lord of the rings",
    "game of thrones", "hunger games", "chronicles of narnia",
    "percy jackson", "teenage mutant ninja turtles", "spider-man",
    "captain america", "iron man", "black panther", "doctor strange",
    "black widow", "scarlet witch", "winter soldier", "ant-man",
    "guardians of the galaxy", "star-lord", "rocket raccoon",
    "wonder woman", "green lantern", "harley quinn", "teen titans",
    "professor x", "fantastic four", "mr fantastic", "invisible woman",
    "human torch", "mickey mouse", "donald duck", "looney tunes",
    "bugs bunny", "scooby doo", "spongebob squarepants", "power rangers",
    "hello kitty", "my little pony", "paw patrol", "peppa pig",
    "dora the explorer", "curious george", "sesame street", "big bird",
    "winnie the pooh", "cat in the hat", "green eggs",
    "diary of a wimpy kid", "dog man", "captain underpants",
    "jurassic park", "jurassic world", "king kong", "james bond",
    "mission impossible", "fast and furious", "maze runner",
    "deathly hallows", "boy who lived", "diagon alley",
    "millennium falcon", "death star", "baby yoda",
    "breaking bad", "walter white", "stranger things", "squid game",
    "rick and morty", "south park", "family guy", "the simpsons",
    "dragon ball", "my hero academia", "attack on titan", "demon slayer",
    "jujutsu kaisen", "fullmetal alchemist", "death note",
    "hunter x hunter", "fairy tail", "sailor moon", "spirited away",
    "studio ghibli", "toy story", "buzz lightyear", "finding nemo",
    "the lion king", "coca-cola", "coca cola", "mcdonald's", "mcdonalds",
    "nintendo switch", "super mario", "legend of zelda", "final fantasy",
    "call of duty", "grand theft auto", "five nights at freddy",
    "warner bros", "universal studios", "walt disney",
    "marvel studios", "dc comics", "new york times", "wall street journal",
    "washington post", "national geographic", "time magazine",
    "super bowl", "world cup", "olympic games", "taylor swift",
    "michael jackson", "elvis presley", "the beatles", "led zeppelin",
    "pink floyd", "space marine", "t-800", "platform 9",
]

# Single distinctive words (matched on word boundaries, case-insensitively).
# Deliberately excludes ordinary dictionary words (dragon, magic, storm, ...).
TM_WORDS = [
    "harry", "potter", "zelda",
    "hogwarts", "voldemort", "hermione", "dumbledore", "snape", "hagrid",
    "malfoy", "dobby", "quidditch", "muggle", "horcrux", "patronus",
    "gryffindor", "slytherin", "hufflepuff", "ravenclaw", "azkaban",
    "butterbeer", "hogsmeade", "lovegood", "weasley", "granger", "jedi", "sith", "darth", "skywalker", "vader", "yoda", "chewbacca", "kenobi",
    "tatooine", "coruscant", "naboo", "mustafar", "dagobah", "bespin",
    "alderaan", "hoth", "endor", "lightsaber", "stormtrooper", "mandalorian",
    "grogu", "ahsoka", "anakin", "padme", "amidala", "palpatine", "dooku",
    "grievous", "jabba", "lando",
    "spock", "kirk", "klingon", "vulcan", "borg", "tribble",
    "gandalf", "frodo", "aragorn", "legolas", "gimli", "gollum", "sauron",
    "saruman", "galadriel", "elrond", "mordor", "rivendell", "gondor",
    "rohan", "smaug", "balrog", "minas", "tirith", "bilbo", "samwise",
    "westeros", "khaleesi", "daenerys", "tyrion", "stark", "lannister",
    "targaryen", "winterfell",
    "katniss", "peeta", "panem", "aslan",
    "pokemon", "pikachu", "charizard", "bulbasaur", "squirtle", "mewtwo",
    "pokeball",
    "naruto", "goku", "vegeta", "luffy", "ichigo", "eren", "tanjiro",
    "nezuko", "sasuke", "kakashi", "itachi", "madara", "zoro", "sanji",
    "frieza", "gohan", "piccolo", "krillin", "trunks",
    "mario", "luigi", "bowser", "yoshi", "wario", "ganondorf", "kirby",
    "samus", "pikmin", "tails", "knuckles", "eggman",
    "megaman", "pacman", "tetris", "frogger", "galaga",
    "batman", "superman", "joker", "aquaman", "shazam", "darkseid",
    "gotham", "metropolis", "krypton", "kryptonite", "bane", "riddler",
    "catwoman", "luthor",
    "thanos", "loki", "asgard", "vibranium", "adamantium",
    "wakanda", "ultron", "natasha", "barton", "rhodes", "fury",
    "xavier", "magneto", "cyclops", "gambit", "nightcrawler", "colossus",
    "mystique", "cerebro", "wolverine", "deadpool", "domino",
    "punisher", "daredevil", "elektra", "kingpin", "ghostrider",
    "moonknight", "shehulk",
    "disney", "marvel", "pixar", "lucasfilm", "minions",
    "gru", "shrek", "fiona", "farquaad", "madagascar", "kungfupanda",
    "toothless",
    "elsa", "olaf", "kristoff", "moana", "merida", "rapunzel", "ariel",
 "aladdin", "mulan", "pocahontas", "tiana", "cinderella",
    "snowwhite", "sleepingbeauty", "tinkerbell", "peterpan", "neverland",
    "simba", "nala", "mufasa", "timon", "pumbaa", "stitch", "lilo",
    "dumbo", "bambi", "pinocchio", "geppetto", "hercules", "tarzan",
    "woody", "jessie", "slinky", "forky", "wazowski",
    "dory", "nemo", "marlin",
    "transformers", "optimus", "megatron", "bumblebee", "starscream",
    "soundwave", "cybertron",
    "skynet", "xenomorph", "godzilla", "mothra", "ghidorah",
    "gremlins", "ghostbusters", "slimer", "beetlejuice", "addams",
    "gomez", "morticia", "wednesday",
    "krueger", "voorhees", "myers", "chucky", "leatherface", "pinhead",
    "candyman", "pennywise", "jigsaw", "annabelle", "conjuring",
    "insidious",
    "lego", "barbie", "nerf", "hasbro", "mattel", "fisherprice",
    "playdoh", "monopoly", "yahtzee", "scrabble", "trivialpursuit",
    "nike", "adidas", "puma", "reebok", "underarmour", "newbalance",
    "converse", "yeezy",
    "starbucks", "dunkin", "pepsi", "gatorade", "redbull",
    "dasani", "evian", "perrier",
    "kleenex", "bandaid", "qtip", "velcro", "sharpie", "postit",
    "tupperware",
    "oreo", "cheerios", "cheetos", "doritos", "pringles", "fritos",
    "goldfish", "poptarts", "luckycharms", "frootloops", "capncrunch",
    "frostedflakes", "cocoapuffs", "trix",
    "bigmac", "whopper", "happymeal", "chickfila", "wendys", "arbys",
    "tacobell", "chipotle", "panera", "dominos", "pizzahut", "papajohns",
    "tesla", "cybertruck", "spacex", "starlink",
    "mustang", "corvette", "silverado", "wrangler", "escalade",
    "rangerover",
    "macbook", "ipad", "ipod", "airpods", "siri", "appstore", "itunes",
    "gmail", "youtube", "pixel", "playstation", "xbox", "linkedin",
    "chatgpt", "openai", "anthropic", "gemini", "alexa",
    "uber", "lyft", "doordash", "grubhub", "ubereats", "airbnb",
    "expedia", "kayak", "priceline", "tripadvisor",
    "kindle", "wholefoods", "etsy", "shopify", "walmart",
    "costco", "ikea", "homedepot", "bestbuy", "gamestop", "walgreens",
    "kroger", "traderjoes", "publix", "wegmans",
    "visa", "mastercard", "amex", "paypal", "venmo", "cashapp",
    "zelle", "stripe", "coinbase",
    "nfl", "nba", "mlb", "nhl", "fifa", "uefa", "nascar", "wwe",
    "ufc", "espn", "nickelodeon", "cartoonnetwork", "adultswim",
 "syfy", "hallmark",
    "homer", "marge", "bart", "krusty", "springfield",
    "stewie", "quagmire",
    "cartman", "kyle", "kenny",
    "patrick", "squidward", "krabby", "plankton",
    "marceline", "mordecai", "rigby",
    "dipper", "mabel",
    "phineas", "ferb", "kimpossible", "dannyphantom", "timmy",
    "jimmyneutron", "dexter", "powerpuff", "mojojojo", "samuraijack",
    "starfire", "beastboy",
    "aang", "katara", "sokka", "zuko", "iroh", "azula", "korra", "toph",
    "voltron", "jarvis",
    "holmes", "watson", "poirot", "marple",
    "hobbit", "dune", "arrakis", "atreides", "harkonnen", "fremen",
    "sandworm", "ansible", "vogon", "zaphod", "marvin", "trillian",
    "discworld", "pratchett", "rincewind", "vimes", "weatherwax",
    "egwene", "nynaeve", "moraine", "sedai",
    "stormlight", "kaladin", "shallan", "dalinar", "szeth", "radiant",
    "shardblade", "mistborn", "kandra", "allomancy", "kelsier", "sazed",
    "kvothe", "chandrian", "temerant",
    "malazan", "dragnipur",
    "rocinante", "holden", "naomi", "draper", "protomolecule",
    "warhammer", "adeptus", "astartes", "horus", "ork", "eldar",
    "necron", "tyranid",
    "planeswalker", "jace", "liliana", "chandra", "garruk",
    "yugioh", "kaiba", "exodia", "blueeyes",
    "digimon", "agumon", "gabumon",
    "beyblade", "bakugan",
    "streetfighter", "chunli", "hadouken", "shoryuken",
    "scorpion", "subzero", "raiden",
    "masterchief", "cortana", "warcraft", "starcraft", "diablo", "overwatch",
    "ahri", "jinx", "yasuo", "garen", "darius", "teemo",
    "valorant", "jett", "sova",
    "skyrim", "dovahkiin", "fusrodah", "morrowind", "pipboy", "nukacola",
    "witcher", "geralt", "ciri", "yennefer", "tossacoin",
    "nightcity", "silverhand",
    "eldenring", "bloodborne", "sekiro",
    "breathofthewild", "ocarina", "majora",
    "tomnook", "isabelle", "splatoon", "inkling", "metroid",
    "fireemblem", "xenoblade", "bioshock", "rapture", "bigdaddy", "littlesister", "wouldyoukindly",
    "glados", "chell", "wheatley", "aperture",
    "blackmesa",
    "teamfortress", "demoman",
    "left4dead", "counterstrike", "dust2",
    "astarion", "shadowheart", "karlach", "laezel",
    "originalsin", "discoelysium", "dubois", "kimkitsuragi",
    "outerwilds", "hearthian", "nomai", "eyesoftheuniverse",
    "federalbureau", "faden", "cauldronlake", "sagaanderson",
    "raccooncity", "leon", "wesker",
    "pyramidhead", "alessa", "fogworld", "fatalframe", "projectzero",
    "penumbra", "outlast", "mountmassive", "layersoffear", "phasmophobia",
    "ishimura", "necromorph",
    "dunwall", "corvo",
    "sarif", "shodan",
    "agent47",
    "tombraider", "croft",
    "nathan", "sully",
    "kratos", "atreus", "mimir", "ragnarok", "yggdrasil", "baldur",
    "freya",
    "aloy", "hephaestus", "tallneck", "thunderjaw", "zerodawn",
    "sakai",
    "milesmorales",
    "cordyceps",
    "becomehuman", "cyberlife", "deviant",
    "quantumbreak",
]

_PHRASE_RE = re.compile(
    "|".join(sorted(set(TM_PHRASES), key=len, reverse=True)), re.I)
_WORD_RE = re.compile(
    r"\b(" + "|".join(sorted(set(TM_WORDS), key=len, reverse=True)) + r")\b",
    re.I)
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z\-']*")


def tm_hits(text):
    """Exact trademark hits: list of (kind, matched_text)."""
    out = []
    for m in _PHRASE_RE.finditer(text):
        out.append(("phrase", m.group(0)))
    for m in _WORD_RE.finditer(text):
        out.append(("word", m.group(0)))
    return out


def _deletes2(w):
    out = set()
    n = len(w)
    for i in range(n):
        out.add(w[:i] + w[i + 1:])
    for i in range(n):
        for j in range(i + 1, n):
            out.add(w[:i] + w[i + 1:j] + w[j + 1:])
    return out


# SymSpell-style delete-variant index: catches substitutions, insertions,
# deletions and 1-2 letter swaps ("Hairy Potter" vs "Harry Potter").
_DELIDX = defaultdict(set)
for _w in set(TM_WORDS):
    if len(_w) >= 5:
        for _d in _deletes2(_w):
            _DELIDX[_d].add(_w)
_DELIDX = dict(_DELIDX)

_WORDSET = set(TM_WORDS)

# Ordinary English words within edit distance 2 of a blocklist word are NOT
# knockoffs ("stars" vs "stark", "murder" vs "mordor", "house" vs "horus").
# Precomputed from a public-domain wordlist; exact matches still fire above.
def _load_exempt():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "tm_exempt.txt")
    try:
        with open(p, encoding="utf-8") as f:
            return {l.strip() for l in f if l.strip()}
    except OSError:
        return set()

_EXEMPT = _load_exempt()


def _lev(a, b, cap=2):
    """True Levenshtein distance, early-exits above cap."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        rowmin = i
        for j, cb in enumerate(b, 1):
            c = prev[j - 1] if ca == cb else 1 + min(prev[j - 1], prev[j], cur[j - 1])
            cur.append(c)
            if c < rowmin:
                rowmin = c
        if rowmin > cap:
            return cap + 1
        prev = cur
    return prev[-1]


def fuzzy_hits(text):
    """Near-misspellings of blocklist words (true edit distance <= 2).

    Delete-variant index generates candidates (necessary but not sufficient
    for distance <= 2); every candidate is verified with real Levenshtein
    so ordinary words ("beacon", "every", "never") are NOT flagged.
    Returns list of (token, blocklist_word). Skips exact blocklist words
    (reported by tm_hits instead).
    """
    out, seen = [], set()
    for tok in _TOKEN_RE.findall(text):
        t = tok.lower().strip("-'")
        if len(t) < 5 or t in seen:
            continue
        seen.add(t)
        if t in _WORDSET or t in _EXEMPT:
            continue
        cands = set()
        for d in _deletes2(t):
            c = _DELIDX.get(d)
            if c:
                cands |= c
        for c in cands:
            if c != t and abs(len(c) - len(t)) <= 2 and _lev(t, c) <= 2:
                out.append((tok, c))
                break
    return out


def is_tm_clean(text):
    return not tm_hits(text) and not fuzzy_hits(text) \
        and not phrase_fuzzy_hits(text)


# ------------------------------------------- phrase-level fuzzy ("Hairy Potter")
# Thin misspellings of multi-word marks keep the word structure, so compare
# spaceless bigrams/trigrams in name position (capitalized token runs) against
# spaceless blocklist phrases with verified edit distance <= 2.
_PHRASE_SMOOTH = {re.sub(r"[^a-z]", "", p): p for p in TM_PHRASES}
_PHRASE_DELIDX = defaultdict(set)
for _s, _p in _PHRASE_SMOOTH.items():
    if len(_s) >= 8:
        for _d in _deletes2(_s):
            _PHRASE_DELIDX[_d].add(_s)
_PHRASE_DELIDX = dict(_PHRASE_DELIDX)


def phrase_fuzzy_hits(text):
    """Near-misspellings of multi-word marks, e.g. 'Hairy Potter'.

    Returns list of (matched_text, blocklist_phrase). Only runs of
    capitalized tokens (name position) are considered, and the spaceless
    edit distance must be <= 1, so ordinary bigrams ("the forger",
    "the porch") are never flagged.
    """
    toks = [(m.group(0), m.start(), m.end())
            for m in re.finditer(r"[A-Za-z][A-Za-z'\-]*", text)]
    out, seen = [], set()
    for n in (3, 2):
        for i in range(len(toks) - n + 1):
            run = toks[i:i + n]
            if not run[0][0][:1].isupper():
                continue
            if any(len(w[0].strip("-'")) < 3 for w in run):
                continue
            smooth = "".join(re.sub(r"[^A-Za-z]", "", w[0]).lower()
                             for w in run)
            if len(smooth) < 8 or smooth in seen:
                continue
            seen.add(smooth)
            cands = set()
            for d in _deletes2(smooth):
                c = _PHRASE_DELIDX.get(d)
                if c:
                    cands |= c
            for c in cands:
                if abs(len(c) - len(smooth)) <= 2 and _lev(smooth, c) <= 1:
                    span = text[run[0][1]:run[-1][2]]
                    # skip if it is really the exact phrase (handled by tm_hits)
                    if span.lower() in TM_PHRASES:
                        break
                    out.append((span, _PHRASE_SMOOTH[c]))
                    break
    return out


# ------------------------------------------- lineage protection
# Factual references to the network's OWN catalog records are citations, not
# knockoffs: "Based on AI Darth Vader (JAH-AI-PER-001)", "Case Study:"
# chapter titles, quoted record titles, and record IDs are masked before
# sanitizing and restored afterwards, so attribution links stay truthful.
_PROTECT_RES = [
    re.compile(r"Based on [^.\n\x00]{0,160}", re.I),
    re.compile(r"Inspired by [^.\n\x00]{0,160}", re.I),
    re.compile(r"Real record on the shelf:[^\x00]*?(?=\n\n|\Z)", re.I | re.S),
    re.compile(r"The catalog describes it this way:[^\x00]*?(?=\n\n|\Z)",
               re.I | re.S),
    re.compile(r"\u201c[^\u201d\x00]{0,160}\u201d"),
    re.compile(r"JAH-(?:AI|LEAK|SPEC|MALL|BOOK|DICT|WORD)-[A-Za-z0-9]+"),
]


def sanitize_book_text(text, g):
    """sanitize_text, but lineage citations to network records are masked
    first and restored after, so factual attribution is never rewritten.
    "Case Study:" chapter titles and "Real record on the shelf:" chapter
    bodies pass through untouched: those chapters are explicitly framed as
    discussions OF the cited record (label, quoted title, catalog blurb,
    study questions about it)."""
    if text.startswith("Case Study:") or "Real record on the shelf:" in text:
        return text, 0
    spans = []

    def _hold(m):
        spans.append(m.group(0))
        return "\x00%d\x00" % (len(spans) - 1)

    masked = text
    for rx in _PROTECT_RES:
        masked = rx.sub(_hold, masked)
    new, n = sanitize_text(masked, g)
    for i in range(len(spans) - 1, -1, -1):
        new = new.replace("\x00%d\x00" % i, spans[i])
    assert "\x00" not in new, "unrestored lineage placeholder"
    return new, n


# ---------------------------------------------------------------- sanitize
# Invented-syllable pools (same family as the book generator's person names:
# provably original, nothing resembling real authors or marks).
_NA = ["Ka", "Mi", "Ro", "Ta", "Se", "Lu", "Na", "Ve", "Ri", "Do", "Fa",
       "Ze", "Sha", "Bel", "Cor", "Del", "Fen", "Hal", "Win", "Tor"]
_NB = ["ren", "sha", "dor", "ven", "mir", "tal", "nor", "lia", "kem",
       "dara", "thon", "wick", "mar", "ston", "fell", "gwen", "hal",
       "bris", "cott", "mere", "lith", "vane", "soul", "crest"]


def _invented(g):
    w = g.pick(_NA) + g.pick(_NB)
    # paranoia: never emit something that itself trips the guard
    for _ in range(8):
        if is_tm_clean(w):
            return w
        w = g.pick(_NA) + g.pick(_NB)
    return w


def _match_case(new, old):
    if old[:1].isupper():
        return new[:1].upper() + new[1:]
    return new


def sanitize_text(text, g):
    """Replace every trademarked/knockoff span with an invented substitute.

    Each distinct violating string gets ONE substitute per call, applied to
    every occurrence (so "Lumir ... Lumir" stays consistent). g is a G-style
    rng (needs .pick); it is only drawn from when a hit exists, so clean
    text is byte-identical. Draw order is alphabetical for determinism.
    Returns (new_text, n_replacements).
    """
    # 1. collect every distinct violating string
    bad = set()
    for _k, m in tm_hits(text):
        bad.add(m)
    for tok, _b in fuzzy_hits(text):
        bad.add(tok)
    for span, _b in phrase_fuzzy_hits(text):
        bad.add(span)
    if not bad:
        return text, 0

    # 2. one invented substitute per distinct string (deterministic order)
    subs = {}
    for s in sorted(bad, key=str.lower):
        w = _invented(g)
        subs[s.lower()] = w

    # 3. single pass, longest match first so phrases beat their sub-words
    pat = re.compile(
        r"(?<![A-Za-z])(" +
        "|".join(re.escape(s) for s in sorted(bad, key=len, reverse=True)) +
        r")(?![A-Za-z])", re.I)

    n = 0

    def _sub(m):
        nonlocal n
        n += 1
        return _match_case(subs[m.group(0).lower()], m.group(0))

    return pat.sub(_sub, text), n


def sanitize_title(title, g):
    """Regenerate-safe title check helper: returns (title, changed)."""
    if is_tm_clean(title):
        return title, False
    new, _ = sanitize_text(title, g)
    return new, True
