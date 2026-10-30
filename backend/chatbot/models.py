import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_id = models.CharField(max_length=180, db_index=True)
    language = models.CharField(max_length=8, default="en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["owner_id", "-updated_at"])]


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    class Source(models.TextChoices):
        MOCK = "mock", "Synthetic demo"
        CONVERSATION = "conversation", "Local conversational reply"
        KNOWLEDGE = "knowledge", "Verified knowledge"
        LLM = "llm", "Grounded LLM"
        MOODLE = "moodle", "Authorized Moodle service"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, related_name="messages", on_delete=models.CASCADE)
    role = models.CharField(max_length=12, choices=Role.choices)
    text = models.TextField(max_length=4000)
    language = models.CharField(max_length=8, default="en")
    intent = models.CharField(max_length=80, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=16, choices=Source.choices, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Feedback(models.Model):
    class Rating(models.TextChoices):
        HELPFUL = "helpful", "Helpful"
        NOT_HELPFUL = "not_helpful", "Not helpful"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, related_name="feedback", on_delete=models.CASCADE)
    message = models.ForeignKey(ChatMessage, related_name="feedback", on_delete=models.CASCADE)
    owner_id = models.CharField(max_length=180, db_index=True)
    rating = models.CharField(max_length=16, choices=Rating.choices)
    comment = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "owner_id"], name="one_feedback_per_user_message")]


class LexiconEntry(models.Model):
    class Verification(models.TextChoices):
        SYNTHETIC = "synthetic", "Synthetic demo"
        PENDING = "pending", "Pending review"
        VERIFIED = "verified", "Verified institutional source"
        REJECTED = "rejected", "Rejected"

    class Language(models.TextChoices):
        ENGLISH = "en", "English"
        SWAHILI = "sw", "Kiswahili"
        MIXED = "mixed", "English–Kiswahili"

    class TranslationStatus(models.TextChoices):
        MISSING = "missing", "Kiswahili equivalent missing"
        PROPOSED = "proposed", "Proposed; needs review"
        VERIFIED = "verified", "Verified by reviewer"
        NOT_APPLICABLE = "not_applicable", "Not applicable"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canonical = models.CharField(max_length=180)
    language = models.CharField(max_length=8, choices=Language.choices)
    synonyms = models.JSONField(default=list, blank=True)
    spelling_variants = models.JSONField(default=list, blank=True)
    abbreviations = models.JSONField(default=list, blank=True)
    intent = models.CharField(max_length=80, db_index=True)
    domain = models.CharField(max_length=80, blank=True)
    allowed_roles = models.JSONField(default=list, blank=True)
    related_terms = models.JSONField(default=list, blank=True)
    example_queries = models.JSONField(default=list, blank=True)
    swahili_equivalent = models.CharField(max_length=240, blank=True)
    english_synonyms = models.JSONField(default=list, blank=True)
    swahili_synonyms = models.JSONField(default=list, blank=True)
    mixed_expressions = models.JSONField(default=list, blank=True)
    abbreviation_variants = models.JSONField(default=list, blank=True)
    service_area = models.CharField(max_length=100, blank=True, db_index=True)
    page_label = models.CharField(max_length=180, blank=True)
    navigation_path = models.CharField(max_length=500, blank=True)
    context_notes = models.TextField(blank=True)
    translation_status = models.CharField(max_length=20, choices=TranslationStatus.choices, default=TranslationStatus.MISSING)
    translation_source = models.CharField(max_length=500, blank=True)
    reviewer = models.CharField(max_length=180, blank=True)
    lexicon_version = models.CharField(max_length=40, default="1.0")
    response_text = models.TextField(blank=True)
    source_reference = models.CharField(max_length=500, blank=True)
    provenance = models.CharField(max_length=500)
    verification_status = models.CharField(max_length=12, choices=Verification.choices, default=Verification.PENDING)
    confidence_threshold = models.FloatField(default=0.60)
    needs_clarification_below = models.FloatField(default=0.45)
    is_active = models.BooleanField(default=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["intent", "language", "canonical"]
        constraints = [models.UniqueConstraint(fields=["canonical", "language", "intent"], name="unique_lexicon_phrase_language_intent")]

    def clean(self):
        errors = {}
        confidence = self.confidence_threshold
        clarification = self.needs_clarification_below
        if confidence is None or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            errors["confidence_threshold"] = "Confidence threshold must be between 0 and 1."
        if clarification is None or not isinstance(clarification, (int, float)) or not 0 <= clarification <= 1:
            errors["needs_clarification_below"] = "Clarification threshold must be between 0 and 1."
        if isinstance(confidence, (int, float)) and isinstance(clarification, (int, float)) and clarification > confidence:
            errors["needs_clarification_below"] = "Clarification threshold cannot exceed the match threshold."
        if self.translation_status == self.TranslationStatus.VERIFIED and not all([
            self.swahili_equivalent, self.translation_source, self.reviewer, self.reviewed_at
        ]):
            errors["translation_status"] = "Verified Kiswahili translations need an equivalent, source, reviewer and review date."
        if self.translation_status == self.TranslationStatus.PROPOSED and (self.swahili_equivalent or self.swahili_synonyms) and not self.translation_source:
            errors["translation_source"] = "Proposed Kiswahili content needs a provenance/source note."
        if self.verification_status == self.Verification.VERIFIED and not all([
            self.source_reference, self.provenance, self.reviewer, self.reviewed_at
        ]):
            errors["verification_status"] = "Verified institutional terms require source, provenance, reviewer and review date."
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"{self.canonical} [{self.language}/{self.intent}]"


class KnowledgeDocument(models.Model):
    class Verification(models.TextChoices):
        SYNTHETIC = "synthetic", "Synthetic demo"
        PENDING = "pending", "Pending review"
        VERIFIED = "verified", "Verified institutional source"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=240)
    body = models.TextField()
    document_id = models.CharField(max_length=120, blank=True, db_index=True)
    source_file = models.CharField(max_length=500, blank=True)
    source_section = models.CharField(max_length=240, blank=True)
    canonical_topic = models.CharField(max_length=180, blank=True, db_index=True)
    source_type = models.CharField(max_length=40, default="text")
    document_version = models.CharField(max_length=80, default="1")
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    embedding = models.JSONField(default=list, blank=True)
    language = models.CharField(max_length=8, choices=LexiconEntry.Language.choices)
    source_url = models.URLField(blank=True)
    provenance = models.CharField(max_length=500)
    reviewer = models.CharField(max_length=180, blank=True)
    owner = models.CharField(max_length=180, blank=True)
    allowed_roles = models.JSONField(default=list, blank=True)
    verification_status = models.CharField(max_length=12, choices=Verification.choices, default=Verification.PENDING)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def clean(self):
        if self.verification_status == self.Verification.VERIFIED:
            missing = [name for name, value in {
                "reviewed_at": self.reviewed_at,
                "reviewer": self.reviewer,
                "source_file": self.source_file,
                "provenance": self.provenance,
            }.items() if not value]
            if missing:
                raise ValidationError({name: "Verified knowledge requires source provenance and a reviewer/date." for name in missing})


class KnowledgeChunk(models.Model):
    """A source-tracked, reviewable retrieval unit derived from an ingested file."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(KnowledgeDocument, related_name="chunks", on_delete=models.CASCADE)
    ordinal = models.PositiveIntegerField()
    title = models.CharField(max_length=240)
    body = models.TextField()
    source_section = models.CharField(max_length=240, blank=True)
    canonical_topic = models.CharField(max_length=180, blank=True)
    interface_role = models.CharField(max_length=40, blank=True)
    language = models.CharField(max_length=8, choices=LexiconEntry.Language.choices, default="en")
    source_type = models.CharField(max_length=40, default="text")
    document_version = models.CharField(max_length=80, default="1")
    content_hash = models.CharField(max_length=64, db_index=True)
    embedding = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document", "ordinal"]
        constraints = [models.UniqueConstraint(fields=["document", "ordinal"], name="unique_knowledge_chunk_ordinal")]


class MoodleAccountLink(models.Model):
    """A server-managed identity mapping; never populated from request fields."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="moodle_identity", on_delete=models.CASCADE)
    moodle_user_id = models.PositiveBigIntegerField(unique=True)
    provenance = models.CharField(max_length=240)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="created_moodle_links", null=True, on_delete=models.SET_NULL)


class EvaluationCase(models.Model):
    class RequestType(models.TextChoices):
        SERVICE = "service", "Service interpretation"
        TRANSLATION = "translation", "Translation request"
        CLARIFICATION = "clarification", "Ambiguous query/clarification"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.CharField(max_length=1000)
    language = models.CharField(max_length=8, choices=LexiconEntry.Language.choices)
    intended_intent = models.CharField(max_length=80)
    reference_answer = models.TextField(blank=True)
    source_reference = models.CharField(max_length=500, blank=True)
    request_type = models.CharField(max_length=20, choices=RequestType.choices, default=RequestType.SERVICE)
    expected_service_area = models.CharField(max_length=100, blank=True)
    expects_clarification = models.BooleanField(default=False)
    translation_status = models.CharField(max_length=20, choices=LexiconEntry.TranslationStatus.choices, default=LexiconEntry.TranslationStatus.NOT_APPLICABLE)
    expected_role = models.CharField(max_length=40, default="student")
    dataset_label = models.CharField(max_length=80, default="synthetic-demo")
    is_synthetic = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["dataset_label", "language", "intended_intent"]


class LexiconRevision(models.Model):
    """Versioned snapshot for auditable, reviewable lexicon changes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.ForeignKey(LexiconEntry, related_name="revisions", on_delete=models.CASCADE)
    version = models.PositiveIntegerField()
    snapshot = models.JSONField()
    change_note = models.CharField(max_length=500, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["entry", "version"], name="unique_lexicon_entry_revision")]


class EvaluationRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evaluation_version = models.CharField(max_length=80)
    dataset_label = models.CharField(max_length=80)
    metrics = models.JSONField(default=dict)
    results = models.JSONField(default=list)
    case_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)


class AuditEvent(models.Model):
    """Metadata-only audit events: never store message text or credentials here."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_id = models.CharField(max_length=180, db_index=True)
    event_type = models.CharField(max_length=80, db_index=True)
    object_id = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
