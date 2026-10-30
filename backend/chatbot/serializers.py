from rest_framework import serializers

from chatbot.models import ChatMessage, Conversation, EvaluationCase, EvaluationRun, Feedback, KnowledgeDocument, LexiconEntry


class ChatMessageRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1000, allow_blank=False, trim_whitespace=True)
    language = serializers.ChoiceField(choices=["en", "sw", "mixed"], default="en")
    queryLanguage = serializers.ChoiceField(choices=["en", "sw", "mixed"], required=False, allow_null=True)
    query_language = serializers.ChoiceField(choices=["en", "sw", "mixed"], required=False, allow_null=True, write_only=True)
    interface_context = serializers.ChoiceField(choices=["student", "teacher", "administrator", "unspecified"], required=False, default="unspecified")
    conversationId = serializers.UUIDField(required=False, allow_null=True)
    conversation_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    context = serializers.JSONField(required=False, default=dict)

    def validate_context(self, value):
        if not isinstance(value, dict) or len(value) > 8:
            raise serializers.ValidationError("Context must be an object with at most eight fields.")
        if any(not isinstance(key, str) or len(key) > 40 for key in value):
            raise serializers.ValidationError("Context field names must be strings of at most 40 characters.")
        if any(not isinstance(item, (str, int, float, bool, type(None))) for item in value.values()):
            raise serializers.ValidationError("Context values must be scalar; user or role identity is never taken from context.")
        return value

    def validate(self, attrs):
        camel = attrs.pop("conversationId", None)
        snake = attrs.pop("conversation_id", None)
        if camel and snake and camel != snake:
            raise serializers.ValidationError({"conversationId": "Provide only one matching conversation identifier."})
        attrs["conversation_id"] = camel or snake
        camel_query = attrs.pop("queryLanguage", None)
        snake_query = attrs.pop("query_language", None)
        if camel_query and snake_query and camel_query != snake_query:
            raise serializers.ValidationError({"queryLanguage": "Provide only one matching query language."})
        attrs["query_language"] = camel_query or snake_query
        return attrs


class ConversationListSerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "language", "created_at", "updated_at", "message_count"]


class MessageReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "text", "language", "intent", "confidence", "source", "created_at"]


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = MessageReadSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "language", "created_at", "updated_at", "messages"]


class FeedbackCreateSerializer(serializers.Serializer):
    conversationId = serializers.UUIDField()
    messageId = serializers.UUIDField()
    rating = serializers.ChoiceField(choices=Feedback.Rating.choices)
    comment = serializers.CharField(max_length=1000, allow_blank=True, required=False, default="")


class KnowledgeSearchSerializer(serializers.ModelSerializer):
    verificationStatus = serializers.CharField(source="verification_status")
    sourceUrl = serializers.CharField(source="source_url", allow_blank=True)

    class Meta:
        model = KnowledgeDocument
        fields = ["id", "title", "body", "language", "sourceUrl", "verificationStatus", "reviewed_at"]


class LexiconReadSerializer(serializers.ModelSerializer):
    verificationStatus = serializers.CharField(source="verification_status")
    translationStatus = serializers.CharField(source="translation_status")
    serviceArea = serializers.CharField(source="service_area")
    pageLabel = serializers.CharField(source="page_label")
    navigationPath = serializers.CharField(source="navigation_path")
    swahiliEquivalent = serializers.CharField(source="swahili_equivalent", allow_blank=True)
    englishSynonyms = serializers.JSONField(source="english_synonyms")
    swahiliSynonyms = serializers.JSONField(source="swahili_synonyms")
    mixedExpressions = serializers.JSONField(source="mixed_expressions")
    contextNotes = serializers.CharField(source="context_notes", allow_blank=True)
    translationSource = serializers.CharField(source="translation_source", allow_blank=True)
    sourceReference = serializers.CharField(source="source_reference", allow_blank=True)
    reviewedAt = serializers.DateTimeField(source="reviewed_at", allow_null=True)

    class Meta:
        model = LexiconEntry
        fields = ["id", "canonical", "language", "swahiliEquivalent", "synonyms", "englishSynonyms", "swahiliSynonyms", "mixedExpressions", "spelling_variants", "abbreviations", "abbreviation_variants", "related_terms", "example_queries", "intent", "domain", "serviceArea", "pageLabel", "navigationPath", "contextNotes", "allowed_roles", "translationStatus", "translationSource", "reviewer", "lexicon_version", "verificationStatus", "sourceReference", "provenance", "reviewedAt"]


class LexiconInterpretRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=1000, allow_blank=False, trim_whitespace=True)
    language = serializers.ChoiceField(choices=["en", "sw", "mixed"], default="en")
    request_type = serializers.ChoiceField(choices=["service", "translation"], default="service")
    target_language = serializers.ChoiceField(choices=["en", "sw"], required=False)
    interface_context = serializers.ChoiceField(choices=["student", "teacher", "administrator", "unspecified"], required=False, default="unspecified")

    def validate(self, attrs):
        if attrs["request_type"] == "translation" and "target_language" not in attrs:
            raise serializers.ValidationError({"target_language": "Choose en or sw for a translation request."})
        if attrs["request_type"] == "translation" and attrs["language"] in {"en", "sw"} and attrs["target_language"] == attrs["language"]:
            raise serializers.ValidationError({"target_language": "The target language must differ from the query language."})
        return attrs


class EvaluationCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationCase
        fields = ["id", "query", "language", "request_type", "intended_intent", "expected_service_area", "expects_clarification", "translation_status", "reference_answer", "source_reference", "expected_role", "dataset_label", "is_synthetic"]


class EvaluationResultSerializer(serializers.Serializer):
    case_id = serializers.UUIDField()
    predicted_intent = serializers.CharField(max_length=80, allow_blank=True)
    predicted_service_area = serializers.CharField(max_length=100, allow_blank=True)
    response_correct = serializers.BooleanField()
    translation_correct = serializers.BooleanField(required=False, allow_null=True, default=None)
    clarification_appropriate = serializers.BooleanField(required=False, allow_null=True, default=None)


class EvaluationRunCreateSerializer(serializers.Serializer):
    evaluation_version = serializers.CharField(max_length=80)
    dataset_label = serializers.CharField(max_length=80)
    results = EvaluationResultSerializer(many=True, allow_empty=False, max_length=1000)


class EvaluationRunReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationRun
        fields = ["id", "evaluation_version", "dataset_label", "metrics", "case_count", "created_at"]
