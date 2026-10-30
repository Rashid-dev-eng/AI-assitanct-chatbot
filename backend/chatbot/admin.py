from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict
from django.utils import timezone

from chatbot.models import AuditEvent, ChatMessage, Conversation, EvaluationCase, EvaluationRun, Feedback, KnowledgeChunk, KnowledgeDocument, LexiconEntry, LexiconRevision, MoodleAccountLink


@admin.register(LexiconEntry)
class LexiconEntryAdmin(admin.ModelAdmin):
    list_display = ("canonical", "language", "intent", "service_area", "translation_status", "verification_status", "lexicon_version", "is_active", "reviewed_at")
    list_filter = ("language", "translation_status", "verification_status", "is_active", "domain", "service_area")
    search_fields = ("canonical", "swahili_equivalent", "intent", "synonyms", "english_synonyms", "swahili_synonyms", "provenance", "source_reference")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        prior = None
        if change:
            previous = LexiconEntry.objects.get(pk=obj.pk)
            prior = previous.revisions.order_by("-version").values_list("version", flat=True).first() or 0
        super().save_model(request, obj, form, change)
        version = (prior or 0) + 1
        snapshot = model_to_dict(obj)
        snapshot["id"] = str(obj.pk)
        snapshot["reviewed_at"] = obj.reviewed_at.isoformat() if obj.reviewed_at else None
        LexiconRevision.objects.create(entry=obj, version=version, snapshot=snapshot,
                                       change_note="Edited in Django admin", changed_by=request.user)


@admin.register(LexiconRevision)
class LexiconRevisionAdmin(admin.ModelAdmin):
    list_display = ("entry", "version", "changed_by", "created_at")
    readonly_fields = ("entry", "version", "snapshot", "change_note", "changed_by", "created_at")
    list_filter = ("created_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "source_file", "language", "verification_status", "reviewer", "is_active", "reviewed_at", "expires_at")
    list_filter = ("language", "verification_status", "is_active")
    search_fields = ("title", "body", "provenance", "source_file", "canonical_topic")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if obj.verification_status == KnowledgeDocument.Verification.VERIFIED:
            obj.reviewed_at = obj.reviewed_at or timezone.now()
            obj.reviewer = request.user.get_username()
            if not obj.provenance or not obj.source_file:
                raise ValidationError("Verified knowledge must retain its source file and provenance.")
        obj.full_clean()
        super().save_model(request, obj, form, change)


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("title", "document", "ordinal", "source_section", "language")
    search_fields = ("title", "body", "source_section", "canonical_topic", "document__source_file")
    list_filter = ("language", "source_type", "interface_role")
    readonly_fields = tuple(field.name for field in KnowledgeChunk._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EvaluationCase)
class EvaluationCaseAdmin(admin.ModelAdmin):
    list_display = ("query", "language", "intended_intent", "dataset_label", "is_synthetic", "is_active")
    list_filter = ("language", "dataset_label", "is_synthetic", "is_active")
    search_fields = ("query", "intended_intent", "dataset_label")


@admin.register(EvaluationRun)
class EvaluationRunAdmin(admin.ModelAdmin):
    list_display = ("evaluation_version", "dataset_label", "case_count", "created_by", "created_at")
    readonly_fields = ("created_at", "created_by", "metrics", "results", "case_count")


@admin.register(MoodleAccountLink)
class MoodleAccountLinkAdmin(admin.ModelAdmin):
    list_display = ("user", "moodle_user_id", "provenance", "created_by", "created_at")
    search_fields = ("user__username", "user__email", "provenance")
    readonly_fields = ("created_at",)


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    can_delete = False
    readonly_fields = ("id", "role", "language", "intent", "confidence", "source", "created_at")
    fields = ("id", "role", "language", "intent", "confidence", "source", "created_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "owner_id", "language", "created_at", "updated_at")
    list_filter = ("language",)
    search_fields = ("id", "owner_id")
    readonly_fields = ("id", "owner_id", "language", "created_at", "updated_at")
    inlines = (ChatMessageInline,)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "owner_id", "rating", "created_at")
    readonly_fields = ("id", "conversation", "message", "owner_id", "rating", "comment", "created_at")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor_id", "event_type", "object_id")
    list_filter = ("event_type", "created_at")
    search_fields = ("actor_id", "event_type", "object_id")
    readonly_fields = ("id", "actor_id", "event_type", "object_id", "metadata", "created_at")
