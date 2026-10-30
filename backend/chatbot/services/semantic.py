from dataclasses import dataclass
from difflib import SequenceMatcher

from chatbot.models import LexiconEntry
from chatbot.services.normalization import normalize_text, tokens


@dataclass(frozen=True)
class IntentMatch:
    entry: LexiconEntry
    confidence: float
    ambiguous: bool = False


def detect_response_language(requested: str, query: str) -> str:
    if requested in {"en", "sw"}:
        return requested
    normalized = normalize_text(query)
    sw_markers = {"na", "yangu", "iko", "wapi", "tafadhali", "kozi", "kazi", "jaribio", "alama", "ninawezaje", "ninaipata", "kuona", "matokeo", "nisaidie", "kupata", "vya", "kujifunzia"}
    en_markers = {"how", "where", "my", "course", "assignment", "quiz", "grade", "marks", "please", "find"}
    words = set(tokens(normalized))
    return "sw" if len(words & sw_markers) > len(words & en_markers) else "en"


def _aliases(entry: LexiconEntry) -> list[str]:
    values = [entry.canonical]
    if entry.language in {"en", "mixed"}:
        if entry.translation_status in {"proposed", "verified"}:
            values.extend([entry.swahili_equivalent] if entry.swahili_equivalent else [])
        groups = (entry.english_synonyms, entry.mixed_expressions, entry.synonyms, entry.spelling_variants,
                  entry.abbreviations, entry.abbreviation_variants, entry.related_terms, entry.example_queries)
    elif entry.language == "sw":
        groups = (entry.synonyms, entry.spelling_variants, entry.abbreviations, entry.related_terms, entry.example_queries)
    else:
        groups = ()
    if entry.language in {"en", "mixed"} and entry.translation_status in {"proposed", "verified"}:
        values.extend(entry.swahili_synonyms)
    if entry.language in {"sw", "mixed"}:
        values.extend(entry.swahili_synonyms)
    for group in groups:
        if isinstance(group, list):
            values.extend(value for value in group if isinstance(value, str))
    return [normalize_text(value) for value in values if value.strip()]


def _score(query: str, alias: str) -> float:
    if not query or not alias:
        return 0.0
    if query == alias:
        return 0.99
    if f" {alias} " in f" {query} ":
        alias_len = len(tokens(alias))
        query_len = max(1, len(tokens(query)))
        return min(0.94, 0.78 + 0.12 * alias_len / query_len)
    q_tokens, a_tokens = set(tokens(query)), set(tokens(alias))
    if not q_tokens or not a_tokens:
        return 0.0
    overlap = len(q_tokens & a_tokens)
    jaccard = overlap / len(q_tokens | a_tokens)
    # Tolerate a small spelling error in one token, without broad fuzzy matches.
    fuzzy = sum(max((SequenceMatcher(None, word, alias_word).ratio() for alias_word in a_tokens), default=0.0) >= 0.78 for word in q_tokens - a_tokens)
    fuzzy_coverage = (overlap + fuzzy) / max(len(q_tokens), len(a_tokens))
    return max(0.72 * jaccard, min(0.78, 0.70 * fuzzy_coverage))


def match_intent(query: str, language: str, role: str = "student") -> IntentMatch | None:
    normalized_query = normalize_text(query)
    candidates: list[tuple[LexiconEntry, float]] = []
    entries = LexiconEntry.objects.filter(is_active=True, verification_status__in=[
        LexiconEntry.Verification.SYNTHETIC,
        LexiconEntry.Verification.PENDING,
        LexiconEntry.Verification.VERIFIED,
    ])
    for entry in entries:
        if entry.intent == "role_term":
            continue
        if entry.allowed_roles and role not in entry.allowed_roles:
            continue
        if language == "en" and entry.language not in {"en", "mixed"}:
            continue
        if language == "sw" and not (
            entry.language in {"sw", "mixed"}
            or (entry.language == "en" and entry.translation_status in {"proposed", "verified"} and (entry.swahili_equivalent or entry.swahili_synonyms))
        ):
            continue
        confidence = max((_score(normalized_query, alias) for alias in _aliases(entry)), default=0.0)
        if confidence >= entry.needs_clarification_below:
            candidates.append((entry, confidence))
    candidates.sort(key=lambda pair: (pair[1], pair[0].language == language), reverse=True)
    if not candidates:
        return None
    first_entry, first_score = candidates[0]
    ambiguous = any(entry.intent != first_entry.intent and (first_score - score) <= 0.08 for entry, score in candidates[1:])
    return IntentMatch(first_entry, first_score, ambiguous)
