"""
Entity extraction and search-query construction.

Why this module exists
----------------------
Measurement of the live pipeline showed the search queries — not the scorer —
were the bottleneck for asset quality:

1. The previous extractor gated proper nouns on ``str.istitle()``. That test is
   False for every mixed-case or all-caps name, so "GitHub", "OpenAI", "AI",
   "IDE", "API" and "iPhone" were all discarded — precisely the entities that
   make a search specific.

2. With the entity gone, queries fell back to a 4-5 word bag of content words
   ("software industry undergoing massive technology"). Wikimedia Commons ANDs
   search terms, and the only files matching five arbitrary words are documents
   with a full text layer. Measured: that query returns 8/8 PDFs, while a
   2-3 term query returns 7-8/8 real images.

The rules here are therefore: recover the entity, and keep queries short.
"""
from __future__ import annotations

import re
from typing import List, Optional

# Tokens that are capitalised only because they open a sentence. Without this
# list "Inside Visual Studio Code…" yields the entity "Inside", and
# "Behind every suggestion…" yields "Behind".
_SENTENCE_OPENERS = frozenset({
    # determiners / pronouns
    "the", "a", "an", "this", "that", "these", "those", "it", "its", "we", "our",
    "they", "their", "them", "you", "your", "he", "she", "his", "her", "i",
    # prepositions / conjunctions
    "in", "on", "at", "by", "for", "with", "from", "to", "of", "as", "into",
    "onto", "over", "under", "above", "below", "behind", "beyond", "inside",
    "outside", "across", "through", "during", "before", "after", "since",
    "until", "while", "and", "but", "or", "so", "because", "although",
    "though", "if", "when", "where", "whether", "than", "then",
    # common adverbs / sentence starters
    "now", "here", "there", "today", "instead", "however", "therefore",
    "meanwhile", "finally", "first", "second", "third", "next", "also",
    "still", "yet", "just", "even", "once", "often", "always", "never",
    "every", "each", "some", "many", "most", "much", "more", "less", "few",
    "both", "all", "any", "another", "such", "same", "other", "own",
    # verbs / generic openers seen in narration
    "is", "are", "was", "were", "be", "been", "being", "has", "have", "had",
    "do", "does", "did", "can", "could", "will", "would", "should", "may",
    "might", "must", "let", "make", "made", "get", "got", "give", "take",
    "what", "which", "who", "how", "why", "whose",
})

# Generic nouns that are capitalised in headline-style scripts but are not
# entities worth searching for by name.
_GENERIC_CAPS = frozenset({
    "software", "hardware", "technology", "company", "companies", "developer",
    "developers", "engineer", "engineers", "team", "teams", "user", "users",
    "customer", "customers", "product", "products", "platform", "service",
    "services", "system", "systems", "tool", "tools", "data", "code", "codebase",
    "internet", "web", "cloud", "model", "models", "agent", "agents", "feature",
    "features", "interface", "dashboard", "website", "screenshot", "video",
    "image", "market", "industry", "business", "world", "people", "person",
})

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9.+&'’-]*")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

# An acronym worth keeping: 2-6 characters, all upper (AI, IDE, API, GPU, SaaS
# is mixed so it is caught by the internal-capital rule instead).
_ACRONYM = re.compile(r"^[A-Z0-9]{2,6}$")
# Internal capital or digit — GitHub, OpenAI, iPhone, PostgreSQL, S3, GPT4.
_INTERNAL_CAP = re.compile(r"^[A-Za-z][A-Za-z0-9.+&'’-]*[A-Z0-9]")

# Words that must never become a standalone acronym entity.
_ACRONYM_STOPLIST = frozenset({"AN", "AS", "AT", "BE", "BY", "DO", "GO", "IF",
                               "IN", "IS", "IT", "NO", "OF", "ON", "OR", "SO",
                               "TO", "UP", "US", "WE", "AND", "BUT", "FOR",
                               "NOT", "THE", "YOU", "ALL", "CAN", "HAS", "HAD"})


def _looks_like_entity(token: str, *, sentence_initial: bool) -> bool:
    """Decide whether a single token names something searchable."""
    bare = token.strip(".,!?\"'();:—–")
    if len(bare) < 2:
        return False

    lower = bare.lower()

    # All-caps acronyms count wherever they appear (AI, IDE, API).
    if _ACRONYM.match(bare) and bare.upper() not in _ACRONYM_STOPLIST:
        return True

    if lower in _GENERIC_CAPS:
        return False

    # A capital inside the word means the capitalisation is intrinsic, not
    # positional: GitHub, OpenAI, PostgreSQL — and also iPhone, eBay, macOS,
    # which begin lower-case, so this test comes before the initial-capital
    # gate below.
    if any(c.isupper() for c in bare[1:]):
        return True

    if not bare[0].isupper():
        return False

    # Plain Titlecase: trust it unless it is only capitalised because it opens
    # the sentence.
    if sentence_initial:
        if lower in _SENTENCE_OPENERS:
            return False
        # Sentence-initial verb forms ("Showing…", "Introducing…", "Announced…")
        # are capitalised by position, not because they name anything.
        if len(lower) > 4 and lower.endswith(("ing", "ed")):
            return False

    return lower not in _SENTENCE_OPENERS


def _extract_with_position(text: str, limit: int = 4) -> List[tuple]:
    """(entity, started_the_sentence) pairs, in reading order."""
    found: List[tuple] = []

    for sentence in _SENTENCE_SPLIT.split(text or ""):
        tokens = _WORD.findall(sentence)
        run: List[str] = []
        run_initial = False
        for i, token in enumerate(tokens):
            if _looks_like_entity(token, sentence_initial=(i == 0)):
                if not run:
                    run_initial = i == 0
                run.append(token.strip(".,!?\"'();:—–"))
            else:
                if run:
                    found.append((" ".join(run), run_initial))
                    run = []
        if run:
            found.append((" ".join(run), run_initial))

    seen: set = set()
    out: List[tuple] = []
    for e, initial in found:
        key = e.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append((e, initial))
        if len(out) >= limit:
            break
    return out


def extract_entities(text: str, limit: int = 4) -> List[str]:
    """
    Named entities in reading order, adjacent tokens merged.

    "Inside Visual Studio Code, the editor…" -> ["Visual Studio Code"]
    "GitHub Copilot has changed…"            -> ["GitHub Copilot"]
    "Microsoft reports that developers…"     -> ["Microsoft"]
    """
    return [e for e, _ in _extract_with_position(text, limit)]


def primary_entity(text: str) -> Optional[str]:
    """The most useful entity to search for, or None if the line names nothing."""
    ents = _extract_with_position(text, limit=4)
    if not ents:
        return None
    # Rank: a word capitalised mid-sentence is far more likely to be a real
    # name than one that merely opens the sentence; then prefer the longer
    # form ("Visual Studio Code" over "Visual"); then reading order.
    ranked = sorted(
        enumerate(ents),
        key=lambda pair: (pair[1][1], -len(pair[1][0].split()), pair[0]),
    )
    best = ranked[0][1][0]
    # Cap at three words so the query stays short.
    return " ".join(best.split()[:3])


# ── Query construction ───────────────────────────────────────────────────────

# One qualifier per intent. Measurement showed 2-3 total terms is the sweet
# spot on Commons; more than that and only text-layer documents match.
_INTENT_QUALIFIER = {
    "product_ui": "interface",
    "screenshot": "screenshot",
    "screen_recording": "screenshot",
    "website": "website",
    "logo": "logo",
    "data_visualization": "chart",
    "diagram": "diagram",
    "illustration": "illustration",
    "news_reference": "news",
    "historical": "history",
    "document": "document",
    "person": "portrait",
    "location": "",
    "stock_footage": "",
    "abstract_broll": "",
}

_CONTENT_STOP = frozenset({
    # function words
    "that", "this", "with", "from", "they", "their", "there", "these", "those",
    "when", "what", "where", "which", "while", "would", "could", "should",
    "have", "been", "were", "will", "into", "over", "about", "after", "before",
    "during", "through", "than", "then", "them", "your", "our", "its", "also",
    "every", "each", "some", "many", "such", "another", "instead", "behind",
    "inside", "once", "just", "even", "only", "more", "most", "very",
    # verbs — rarely useful in an image search
    "means", "needed", "sits", "running", "changed", "reports", "accept",
    "suggests", "trained", "shipping", "spend", "write", "writing", "using",
    "emerge", "emerging", "undergoing", "allows", "shows", "makes", "build",
    "building", "create", "creating", "analyze", "process", "processing",
    # scale/degree adjectives — they add no visual meaning to a query
    "roughly", "entire", "enormous", "massive", "underlying", "small", "large",
    "larger", "smaller", "huge", "tiny", "far", "near", "public", "private",
    "modern", "global", "digital", "complex", "simple", "different", "several",
    "billions", "millions", "thousands", "percent", "first", "next", "last",
})


def content_terms(text: str, count: int = 2) -> List[str]:
    """
    Distinctive plain words, used when a line names no entity.

    Prefers an ADJACENT pair of content words, because in narration those are
    usually a compound noun naming the thing to show ("data center",
    "engineering team", "solar panel"). Falls back to reading order.
    """
    raw = [w.lower().strip(".,!?\"'();:") for w in _WORD.findall(text or "")]

    def eligible(w: str) -> bool:
        return len(w) > 3 and w not in _CONTENT_STOP

    # First adjacent pair of eligible words — the likely compound noun.
    if count >= 2:
        for i in range(len(raw) - 1):
            if eligible(raw[i]) and eligible(raw[i + 1]):
                return [raw[i], raw[i + 1]]

    ordered = [w for w in dict.fromkeys(raw) if eligible(w)]
    if not ordered:
        ordered = [w for w in dict.fromkeys(raw) if len(w) > 3]
    return ordered[:count]


def build_search_query(text: str, intent: str, max_terms: int = 3) -> str:
    """
    Build a short, entity-led search query.

    Falls back to two distinctive content words when the line names nothing.
    Never returns an empty string.
    """
    entity = primary_entity(text)
    qualifier = _INTENT_QUALIFIER.get(intent, "")

    if entity:
        terms = entity.split()
        if qualifier and len(terms) < max_terms:
            terms.append(qualifier)
        # A bare acronym ("AI") is too broad to search alone — give it one
        # content word for context.
        if len(terms) < 2:
            have = {x.lower() for x in terms}
            extra = next(
                (t for t in content_terms(text, count=4) if t.lower() not in have),
                None,
            )
            if extra:
                terms.append(extra)
    else:
        terms = content_terms(text, count=2)
        if qualifier and len(terms) < max_terms:
            terms.append(qualifier)

    terms = [t for t in terms if t][:max_terms]
    return " ".join(terms) if terms else (intent.replace("_", " ") or "technology")
