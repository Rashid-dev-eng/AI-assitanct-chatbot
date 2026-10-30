"""Source-filtered hybrid retrieval over reviewed knowledge chunks."""
import math
from dataclasses import dataclass

from django.db.models import Q
from django.utils import timezone

from chatbot.models import KnowledgeChunk, KnowledgeDocument
from chatbot.services.llm import embed_text


@dataclass
class LegacyChunk:
    """Compatibility wrapper for reviewed documents created before chunk ingestion."""
    document: KnowledgeDocument
    title: str
    body: str
    source_section: str = ""
    canonical_topic: str = ""
    embedding: list[float] | None = None


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    norms = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return dot / norms if norms else 0.0


def retrieve_knowledge(query: str, language: str, role: str, limit: int = 5):
    """Return scored chunks; unreviewed, expired, and role-restricted content is excluded."""
    terms = [term.casefold() for term in query.strip().split() if len(term) > 2][:12]
    chunks = KnowledgeChunk.objects.filter(
        document__is_active=True,
        document__verification_status=KnowledgeDocument.Verification.VERIFIED,
        document__reviewed_at__isnull=False,
        document__reviewer__gt="",
    ).filter(Q(document__expires_at__isnull=True) | Q(document__expires_at__gt=timezone.now()))
    if language in {"en", "sw"}:
        chunks = chunks.filter(language__in=[language, "mixed"])
    query_vector = []
    try:
        query_vector = embed_text(query)
    except Exception:
        # Retrieval stays available via keyword scoring if embeddings are offline.
        query_vector = []

    ranked = []
    for chunk in chunks.select_related("document"):
        roles = chunk.document.allowed_roles
        if roles and role not in roles:
            continue
        haystack = f"{chunk.title} {chunk.body} {chunk.canonical_topic} {chunk.source_section}".casefold()
        hits = sum(term in haystack for term in terms)
        lexical = hits / max(len(terms), 1)
        semantic = _cosine(query_vector, chunk.embedding)
        score = max(lexical, semantic if semantic >= 0.42 else 0.0)
        if score >= 0.25:
            ranked.append((score, chunk))
    legacy_docs = KnowledgeDocument.objects.filter(
        is_active=True,
        verification_status=KnowledgeDocument.Verification.VERIFIED,
        reviewed_at__isnull=False,
        reviewer__gt="",
        chunks__isnull=True,
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
    if language in {"en", "sw"}:
        legacy_docs = legacy_docs.filter(language__in=[language, "mixed"])
    for document in legacy_docs.distinct():
        if document.allowed_roles and role not in document.allowed_roles:
            continue
        text = f"{document.title} {document.body} {document.canonical_topic} {document.source_section}".casefold()
        hits = sum(term in text for term in terms)
        score = hits / max(len(terms), 1)
        if score >= 0.25:
            ranked.append((score, LegacyChunk(document, document.title, document.body, document.source_section, document.canonical_topic, document.embedding)))
    ranked.sort(key=lambda item: (item[0], len(item[1].body)), reverse=True)
    return ranked[:limit]


def search_verified_knowledge(query: str, language: str, role: str, limit: int = 5):
    """Compatibility wrapper used by existing API search endpoints."""
    return [chunk.document for _, chunk in retrieve_knowledge(query, language, role, limit)]
