# scorer.py
"""
More robust scorer (regex + substring + lemma + fuzzy)

Key improvements:
 - preserve parentheses/*/^ in normalization so complexity notation stays intact
 - explicit regex detectors for complexity notation families (quadratic, exponential, linear, v+e)
 - expanded phrase lists (singular/plural, contractions)
 - pipeline: regex detectors -> substring -> lemma -> fuzzy (rapidfuzz)
 - returns matched pattern and match type for debugging
"""

import re
from typing import List, Optional, Tuple
from rapidfuzz import fuzz, process

# try to load spaCy for lemmatization; if unavailable, we'll fallback
try:
    import spacy
    nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
except Exception:
    nlp = None

# -------------------------
# Patterns (expanded)
# -------------------------
PEER_INDICATORS = {
    "complexity": [
        "o(n^2)", "o(n*n)", "n^2", "n2", "quadratic", "o(n^3)", "n log n", "o(n log n)", "o(nlogn)",
        "polynomial", "o(v*e)", "o(v+e)", "o(n * k log k)", "o(n*k*log k)", "o(n*k log k)",
        # also include plain textual forms:
        "exponential", "2^n", "o(2^n)"
    ],
    "off_by_one": [
        "off-by-one", "off by one", "n-1", "n + 1", "n+1", "i <= n", "index out of range",
        "one too many", "off by"
    ],
    "missing_base_case": [
        "base case", "if n == 1", "if n == 0", "no base case", "missing base", "if not lst",
        "null checks", "empty list", "empty lists", "don't check empty", "won't check empty", "won't check",
        "skip empty", "forget base", "missing base case", "no base case"
    ],
    "edge_case": [
        "edge case", "handle empty", "handle negative", "watch out for empty", "check for none", "negative",
        "fails with negative", "empty", "null", "ignoring", "odd/even", "odd vs even", "odd and even",
        "odd even", "odd vs even lengths", "odd vs even length"
    ],
    "inefficient": [
        "nested loop", "nested loops", "pairwise", "compare each with every other", "pair wise", "inefficient",
        "n^2", "quadratic", "o(n log n)", "sorting each string", "sort each string",
        "sort each", "sorting each", "o(n * k log k)", "n * k log k", "n k log k"
    ]
}

TEACHER_INDICATORS = {
    "complexity": [
        "o(n)", "linear", "linear time", "o(2^n)", "2^n", "exponential", "o(n log n)", "o(v+e)", "o(v + e)",
        "o(n*k)", "o(n * k)"
    ],
    "off_by_one": [
        "off-by-one", "off by one", "clarify whether n is 1-based", "one-based", "zero-based", "fix index",
        "use <= vs <", "off by"
    ],
    "missing_base_case": [
        "base case", "handle empty", "return 0", "add a base case", "check for empty list", "base-case checks",
        "base case check"
    ],
    "edge_case": [
        "edge case", "handle empty", "handle negative", "watch out for empty", "check for none", "null", "empty keys",
        "fails with negative", "bellman-ford", "odd/even", "odd vs even", "odd even", "odd/even splits"
    ],
    "inefficient": [
        "optimize", "avoid nested", "two-pointer", "linear time", "o(n)", "use hashmap", "use memo", "use dp",
        "inefficient", "o(n*k)", "use letter counts", "letter counts", "count characters"
    ]
}

# -------------------------
# Regex detectors for complexity / numeric forms
# -------------------------
COMPLEXITY_REGEX = {
    # quadratic: O(n^2), O(n*n), n^2, n*n (allow spaces and optional parentheses)
    "quadratic": re.compile(r"\b(?:o\(?\s*n\s*[\^*]\s*2\)?|n\s*[\^*]\s*2|n\s*\*\s*n)\b", flags=re.I),
    # exponential: O(2^n), 2^n, exponential
    "exponential": re.compile(r"\b(?:o\(?\s*2\s*[\^]\s*n\)?|2\s*[\^]\s*n|exponential|2\^n)\b", flags=re.I),
    # linear: O(n), linear time
    "linear": re.compile(r"\b(?:o\(?\s*n\)?|linear(?:\s*time)?)\b", flags=re.I),
    # n log n / n*log n variants
    "nlogn": re.compile(r"\b(?:n\s*(?:\*|\s)?\s*log\s*n|n\s*log\s*n|o\(?\s*n\s*log\s*n\)?)\b", flags=re.I),
    # V+E style
    "vplusE": re.compile(r"\b(?:v\s*[\+&]\s*e|v\s*\+\s*e|v\+e|o\(?\s*v\s*\+\s*e\)?)\b", flags=re.I),
    # n * k log k (anagrams style)
    "n_k_logk": re.compile(r"\b(?:n\s*(?:\*|\s)?\s*k\s*(?:\*|\s)?\s*log\s*k|o\(?\s*n\s*\*\s*k\s*log\s*k\)?)\b", flags=re.I),
    # generic "n * k" or "n k"
    "n_k": re.compile(r"\b(?:n\s*(?:\*|\s)\s*k|n\s+k)\b", flags=re.I)
}

# -------------------------
# Fuzzy settings
# -------------------------
FUZZY_SCORE_THRESHOLD = 82
SHORT_PHRASE_FUZZY_THRESHOLD = 88

# -------------------------
# Normalization & lemma helpers
# -------------------------
def _normalize_keep_paren(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    # keep parentheses and common complexity characters ^ and *
    # replace slashes and vs with spaces so "odd/even" and "odd vs even" compare reliably
    t = t.replace("/", " ")
    t = re.sub(r"\bvs\b", " vs ", t, flags=re.I)
    # collapse multiple spaces, remove stray punctuation except ^ * ( )
    t = re.sub(r"[^0-9A-Za-z\s\^\*\(\)\+\-]", " ", t)
    t = " ".join(t.split())
    return t.lower()

def _lemmatize_tokens(text: str) -> List[str]:
    if not text:
        return []
    if nlp is None:
        # fallback: normalize and split
        return _normalize_keep_paren(text).split()
    doc = nlp(text)
    return [tok.lemma_.lower() for tok in doc if not tok.is_space]

# -------------------------
# Matching pipeline
# -------------------------
def _regex_complexity_detect(text: str) -> Optional[Tuple[str, str]]:
    """Return (key, 'regex') if numeric complexity pattern found."""
    txt = text or ""
    for k, rx in COMPLEXITY_REGEX.items():
        if rx.search(txt):
            return (k, "regex")
    return None

def _contains_any_substring(text: str, patterns: List[str]) -> Optional[str]:
    txt = _normalize_keep_paren(text)
    for p in patterns:
        if p in txt:
            return p
    return None

def _lemma_token_match(text: str, patterns: List[str]) -> Optional[str]:
    tokens = _lemmatize_tokens(text)
    if not tokens:
        return None
    token_set = set(tokens)
    for p in patterns:
        p_norm = _normalize_keep_paren(p)
        p_tokens = p_norm.split()
        # require that all tokens in the pattern are present in doc lemmas (order not required)
        if all(pt in token_set for pt in p_tokens):
            return p
    # also check n-grams presence
    L = len(tokens)
    for n in range(min(5, L), 0, -1):
        for i in range(0, L - n + 1):
            gram = " ".join(tokens[i:i+n])
            for p in patterns:
                if _normalize_keep_paren(p) == gram:
                    return p
    return None

def _fuzzy_match(text: str, patterns: List[str]) -> Optional[Tuple[str, int]]:
    txt = _normalize_keep_paren(text)
    if not txt:
        return None
    try:
        choice, score, _ = process.extractOne(txt, patterns, scorer=fuzz.token_sort_ratio)
    except Exception:
        # fallback manual
        best = (None, 0)
        for p in patterns:
            s = fuzz.token_sort_ratio(txt, p)
            if s > best[1]:
                best = (p, s)
        choice, score = best
    if not choice:
        return None
    short = len(choice.split()) <= 2
    threshold = SHORT_PHRASE_FUZZY_THRESHOLD if short else FUZZY_SCORE_THRESHOLD
    if score >= threshold:
        return (choice, int(score))
    return None

def _matches_any(text: str, patterns: List[str]) -> Optional[Tuple[str, str]]:
    if not text:
        return None
    # 0) regex-based numeric complexity detectors (fast and precise)
    reg = _regex_complexity_detect(text)
    if reg:
        return (reg[0], "regex_complexity")
    # 1) substring
    sub = _contains_any_substring(text, patterns)
    if sub:
        return (sub, "substr")
    # 2) lemma/token match
    lm = _lemma_token_match(text, patterns)
    if lm:
        return (lm, "lemma")
    # 3) fuzzy match (fallback)
    fm = _fuzzy_match(text, patterns)
    if fm:
        pattern, score = fm
        return (pattern, f"fuzzy:{score}")
    return None

# -------------------------
# API
# -------------------------
def score_pair(peer_text: str, teacher_text: str, expected_mistakes: List[str]):
    peer_detected = {}
    teacher_fixed = {}

    for m in expected_mistakes:
        peer_patterns = PEER_INDICATORS.get(m, [])
        teacher_patterns = TEACHER_INDICATORS.get(m, [])

        pm = _matches_any(peer_text or "", peer_patterns)
        tm = _matches_any(teacher_text or "", teacher_patterns)

        peer_detected[m] = (bool(pm), pm[0] if pm else None, pm[1] if pm else None)
        teacher_fixed[m] = (bool(tm), tm[0] if tm else None, tm[1] if tm else None)

    overall_pass = all(peer_detected[m][0] and teacher_fixed[m][0] for m in expected_mistakes)

    return {
        "peer_detected": peer_detected,
        "teacher_fixed": teacher_fixed,
        "pass": overall_pass
    }

# quick smoke
if __name__ == "__main__":
    peer = "Selection sort is O(n log n) and very efficient."
    teacher = "Selection sort is O(n^2), not O(n log n). It is inefficient for large inputs."
    print(score_pair(peer, teacher, ["inefficient", "complexity"]))
