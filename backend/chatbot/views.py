from django.conf import settings
from django.db import connection
from django.db.models import Count
from django.http import Http404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chatbot.models import (
    AuditEvent,
    ChatMessage,
    Conversation,
    EvaluationCase,
    EvaluationRun,
    Feedback,
    LexiconEntry,
    KnowledgeDocument,
    KnowledgeChunk,
)
from chatbot.serializers import (
    ChatMessageRequestSerializer,
    ConversationDetailSerializer,
    ConversationListSerializer,
    EvaluationCaseSerializer,
    EvaluationRunCreateSerializer,
    EvaluationRunReadSerializer,
    FeedbackCreateSerializer,
    KnowledgeSearchSerializer,
    LexiconInterpretRequestSerializer,
    LexiconReadSerializer,
)
from chatbot.services.knowledge import search_verified_knowledge
from chatbot.services.responses import Answer, generate_answer
from chatbot.services.semantic import match_intent
from chatbot.services.tool_registry import trusted_role
from integrations.moodle.adapter import MoodleAdapter


def principal_id(user) -> str:
    """Get only the server-authenticated principal identifier."""
    return str(user.pk)


def record_audit(user, event_type: str, object_id: str = "", metadata: dict | None = None) -> None:
    AuditEvent.objects.create(
        actor_id=principal_id(user),
        event_type=event_type,
        object_id=object_id,
        metadata=metadata or {},
    )


def response_source_reference(answer: Answer) -> list[dict]:
    return answer.source_references


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: OpenApiResponse(description="Backend readiness; never includes secrets.")})
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            return Response({"status": "unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"status": "ok", "mode": "demo" if settings.DEMO_AUTH_MODE and settings.DEBUG else "institutional"})


class KnowledgeStatusView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: OpenApiResponse(description="Ingestion, review, and optional provider readiness counts; contains no secrets.")})
    def get(self, request):
        documents = KnowledgeDocument.objects.filter(is_active=True)
        verified = documents.filter(verification_status=KnowledgeDocument.Verification.VERIFIED, reviewed_at__isnull=False)
        return Response({
            "status": "ready" if verified.exists() else "empty_or_pending",
            "documents": documents.count(),
            "verifiedDocuments": verified.count(),
            "pendingDocuments": documents.filter(verification_status=KnowledgeDocument.Verification.PENDING).count(),
            "chunks": KnowledgeChunk.objects.filter(document__is_active=True).count(),
            "llmConfigured": bool(settings.LLM_API_KEY and settings.LLM_MODEL),
            "embeddingConfigured": bool(settings.LLM_API_KEY and settings.EMBEDDING_MODEL),
            "sourceLimitations": "Only supplied source files are indexed; no live DeLMS crawl or screenshot OCR is performed.",
        })


class IntegrationStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiResponse(description="Sanitized Moodle integration state; no token or URL returned.")})
    def get(self, request):
        return Response(MoodleAdapter().status())


class ChatMessageView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChatMessageRequestSerializer,
        responses={201: OpenApiResponse(description="Answer, conversation identifier, confidence and safe source metadata.")},
    )
    def post(self, request):
        serializer = ChatMessageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        owner = principal_id(request.user)
        conversation_id = data.get("conversation_id")

        if conversation_id:
            conversation = Conversation.objects.filter(pk=conversation_id, owner_id=owner).first()
            if conversation is None:
                raise Http404
        else:
            conversation = Conversation.objects.create(owner_id=owner, language=data["language"])
            record_audit(request.user, "conversation.created", str(conversation.pk), {"mode": "demo" if settings.DEMO_AUTH_MODE else "institutional"})

        query = data["message"]
        # Context is deliberately not accepted as identity, role, or permission proof.
        prior_context = list(conversation.messages.order_by("-created_at").values_list("text", flat=True)[:6])
        answer = generate_answer(query, data["language"], request.user, data.get("query_language"), list(reversed(prior_context)), data.get("interface_context"))
        ChatMessage.objects.create(
            conversation=conversation,
            role=ChatMessage.Role.USER,
            text=query,
            language=answer.language,
        )
        stored_source = ChatMessage.Source.LLM if answer.source == "llm" else (ChatMessage.Source.KNOWLEDGE if answer.source in {"api", "knowledge"} else (ChatMessage.Source.CONVERSATION if answer.source == "conversation" else ChatMessage.Source.MOCK))
        assistant_message = ChatMessage.objects.create(
            conversation=conversation,
            role=ChatMessage.Role.ASSISTANT,
            text=answer.message,
            language=answer.language,
            intent=answer.intent or "",
            confidence=answer.confidence,
            source=stored_source,
        )
        conversation.language = answer.language
        conversation.save(update_fields=["language", "updated_at"])
        record_audit(request.user, "chat.message_processed", str(conversation.pk), {
            "intent": answer.intent or "unmatched",
            "source": answer.source,
            "clarification": answer.needs_clarification,
            "assistant_message_id": str(assistant_message.pk),
        })
        payload = {
            "conversationId": str(conversation.pk),
            "message": answer.message,
            "language": answer.language,
            "source": answer.source,
            "relatedQuestions": answer.related_questions,
            "intent": answer.intent,
            "confidence": answer.confidence,
            "needsClarification": answer.needs_clarification,
            "sourceReferences": response_source_reference(answer),
            "integrationStatus": MoodleAdapter().status()["status"],
            "retrievalStatus": answer.retrieval_status,
            "responseMode": answer.response_mode,
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ConversationListSerializer(many=True)})
    def get(self, request):
        conversations = Conversation.objects.filter(owner_id=principal_id(request.user)).annotate(message_count=Count("messages"))[:100]
        return Response(ConversationListSerializer(conversations, many=True).data)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_owned(self, request, conversation_id):
        conversation = Conversation.objects.filter(pk=conversation_id, owner_id=principal_id(request.user)).first()
        if conversation is None:
            raise Http404
        return conversation

    @extend_schema(responses={200: ConversationDetailSerializer})
    def get(self, request, conversation_id):
        conversation = self.get_owned(request, conversation_id)
        return Response(ConversationDetailSerializer(conversation).data)

    @extend_schema(responses={204: OpenApiResponse(description="Conversation and its messages removed.")})
    def delete(self, request, conversation_id):
        conversation = self.get_owned(request, conversation_id)
        object_id = str(conversation.pk)
        record_audit(request.user, "conversation.deleted", object_id)
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=FeedbackCreateSerializer, responses={201: OpenApiResponse(description="Feedback accepted.")})
    def post(self, request):
        serializer = FeedbackCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        owner = principal_id(request.user)
        conversation = Conversation.objects.filter(pk=data["conversationId"], owner_id=owner).first()
        if conversation is None:
            raise Http404
        message = ChatMessage.objects.filter(pk=data["messageId"], conversation=conversation, role=ChatMessage.Role.ASSISTANT).first()
        if message is None:
            raise Http404
        feedback, created = Feedback.objects.get_or_create(
            message=message,
            owner_id=owner,
            defaults={"conversation": conversation, "rating": data["rating"], "comment": data["comment"]},
        )
        if not created:
            feedback.rating = data["rating"]
            feedback.comment = data["comment"]
            feedback.save(update_fields=["rating", "comment"])
        record_audit(request.user, "feedback.recorded", str(feedback.pk), {"rating": feedback.rating})
        return Response({"status": "recorded"}, status=status.HTTP_201_CREATED)


class KnowledgeSearchView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(parameters=[
        OpenApiParameter("q", str, required=True),
        OpenApiParameter("language", str, required=False, enum=["en", "sw", "mixed"]),
    ], responses={200: KnowledgeSearchSerializer(many=True)})
    def get(self, request):
        query = str(request.query_params.get("q", "")).strip()
        language = str(request.query_params.get("language", "en"))
        if not query or len(query) > 500 or language not in {"en", "sw", "mixed"}:
            return Response({"error": {"code": "validation_error", "message": "Provide q (1–500 characters) and a supported language.", "details": None}}, status=400)
        role = trusted_role(request.user)
        documents = search_verified_knowledge(query, language, role)
        return Response(KnowledgeSearchSerializer(documents, many=True).data)


class LexiconView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: LexiconReadSerializer(many=True)})
    def get(self, request):
        entries = LexiconEntry.objects.all()[:500]
        return Response(LexiconReadSerializer(entries, many=True).data)


class LexiconInterpretView(APIView):
    """Classify a service request or look up a lexicon translation separately."""
    permission_classes = [IsAuthenticated]

    @extend_schema(request=LexiconInterpretRequestSerializer, responses={200: OpenApiResponse(description="Translation lookup or service interpretation; this endpoint does not retrieve a learner record or answer." )})
    def post(self, request):
        serializer = LexiconInterpretRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        role = trusted_role(user)
        match = match_intent(data["query"], data["language"], role)
        if data["request_type"] == "translation":
            target = data["target_language"]
            if not match:
                return Response({"requestType": "translation", "translation": "", "translationStatus": "missing", "targetLanguage": target, "needsClarification": False, "sourceReference": None})
            entry = match.entry
            if match.ambiguous or match.confidence < entry.confidence_threshold:
                return Response({"requestType": "translation", "translation": "", "translationStatus": "missing", "targetLanguage": target, "needsClarification": True, "sourceReference": None})
            if target == "sw":
                translated = entry.swahili_equivalent if entry.translation_status in {"proposed", "verified"} else ""
            else:
                translated = entry.canonical if entry.translation_status in {"proposed", "verified"} else ""
            return Response({
                "requestType": "translation",
                "sourceTerm": entry.canonical,
                "targetLanguage": target,
                "translation": translated,
                "translationStatus": entry.translation_status,
                "needsClarification": False,
                "verificationStatus": entry.verification_status,
                "sourceReference": entry.translation_source or entry.source_reference or None,
                "reviewer": entry.reviewer or None,
                "reviewedAt": entry.reviewed_at,
            })

        if not match or match.ambiguous or match.confidence < match.entry.confidence_threshold:
            return Response({"requestType": "service", "matched": bool(match), "needsClarification": True, "intent": None,
                             "serviceArea": None, "pageLabel": None, "navigationPath": None,
                             "retrieval": "not_attempted"})
        entry = match.entry
        return Response({
            "requestType": "service",
            "matched": True,
            "needsClarification": False,
            "intent": entry.intent,
            "serviceArea": entry.service_area or entry.domain,
            "pageLabel": entry.page_label or entry.canonical,
            "navigationPath": entry.navigation_path or None,
            "sourceReference": entry.source_reference or None,
            "verificationStatus": entry.verification_status,
            "translationStatus": entry.translation_status,
            "confidence": round(match.confidence, 3),
            "retrieval": "separate_step_required",
        })


class EvaluationCasesView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: EvaluationCaseSerializer(many=True)})
    def get(self, request):
        cases = EvaluationCase.objects.filter(is_active=True)[:500]
        return Response(EvaluationCaseSerializer(cases, many=True).data)


class EvaluationRunsView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: EvaluationRunReadSerializer(many=True)})
    def get(self, request):
        runs = EvaluationRun.objects.order_by("-created_at")[:100]
        return Response(EvaluationRunReadSerializer(runs, many=True).data)

    @extend_schema(request=EvaluationRunCreateSerializer, responses={201: EvaluationRunReadSerializer})
    def post(self, request):
        serializer = EvaluationRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cases = {
            str(case.pk): case
            for case in EvaluationCase.objects.filter(
                is_active=True,
                dataset_label=data["dataset_label"],
                pk__in=[item["case_id"] for item in data["results"]],
            )
        }
        if len(cases) != len(data["results"]):
            return Response({"error": {"code": "validation_error", "message": "Each case must be active and belong to the selected approved dataset.", "details": None}}, status=400)
        if len(set(str(item["case_id"]) for item in data["results"])) != len(data["results"]):
            return Response({"error": {"code": "validation_error", "message": "Evaluation results cannot repeat a case.", "details": None}}, status=400)
        expected_ids = set(str(value) for value in EvaluationCase.objects.filter(is_active=True, dataset_label=data["dataset_label"]).values_list("pk", flat=True))
        if set(cases) != expected_ids:
            return Response({"error": {"code": "validation_error", "message": "Include every active case from the selected dataset so runs use the same test set.", "details": None}}, status=400)

        evaluated = []
        intents = set()
        response_correct = 0
        service_correct = 0
        service_count = 0
        translation_correct = 0
        translation_count = 0
        clarification_correct = 0
        clarification_count = 0
        for item in data["results"]:
            case = cases[str(item["case_id"])]
            expected, predicted = case.intended_intent, item["predicted_intent"]
            intents.add(expected)
            response_correct += int(item["response_correct"])
            if case.expected_service_area:
                service_count += 1
                service_correct += int(item["predicted_service_area"] == case.expected_service_area)
            if case.request_type == EvaluationCase.RequestType.TRANSLATION and item.get("translation_correct") is not None:
                translation_count += 1
                translation_correct += int(item["translation_correct"])
            if (case.expects_clarification or case.request_type == EvaluationCase.RequestType.CLARIFICATION) and item.get("clarification_appropriate") is not None:
                clarification_count += 1
                clarification_correct += int(item["clarification_appropriate"])
            evaluated.append({
                "caseId": str(case.pk),
                "intendedIntent": expected,
                "predictedIntent": predicted,
                "intentCorrect": expected == predicted,
                "expectedServiceArea": case.expected_service_area,
                "predictedServiceArea": item["predicted_service_area"],
                "serviceCorrect": expected == predicted and (not case.expected_service_area or item["predicted_service_area"] == case.expected_service_area),
                "responseCorrect": item["response_correct"],
                "requestType": case.request_type,
                "translationCorrect": item.get("translation_correct"),
                "clarificationExpected": case.expects_clarification or case.request_type == EvaluationCase.RequestType.CLARIFICATION,
                "clarificationAppropriate": item.get("clarification_appropriate"),
            })

        per_intent = []
        for intent in sorted(intents):
            tp = sum(row["intendedIntent"] == intent and row["predictedIntent"] == intent for row in evaluated)
            fp = sum(row["intendedIntent"] != intent and row["predictedIntent"] == intent for row in evaluated)
            fn = sum(row["intendedIntent"] == intent and row["predictedIntent"] != intent for row in evaluated)
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            per_intent.append({"intent": intent, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)})
        n = len(evaluated)
        metrics = {
            "queryInterpretationAccuracy": round(sum(row["intentCorrect"] for row in evaluated) / n, 4),
            "serviceMappingAccuracy": round(service_correct / service_count, 4) if service_count else None,
            "responseCorrectness": round(response_correct / n, 4),
            "translationQuality": round(translation_correct / translation_count, 4) if translation_count else None,
            "clarificationAppropriateness": round(clarification_correct / clarification_count, 4) if clarification_count else None,
            "macroPrecision": round(sum(item["precision"] for item in per_intent) / len(per_intent), 4),
            "macroRecall": round(sum(item["recall"] for item in per_intent) / len(per_intent), 4),
            "macroF1": round(sum(item["f1"] for item in per_intent) / len(per_intent), 4),
            "perIntent": per_intent,
        }
        run = EvaluationRun.objects.create(
            evaluation_version=data["evaluation_version"],
            dataset_label=data["dataset_label"],
            metrics=metrics,
            results=evaluated,
            case_count=n,
            created_by=request.user,
        )
        record_audit(request.user, "evaluation.run_created", str(run.pk), {"dataset": run.dataset_label, "case_count": n})
        return Response(EvaluationRunReadSerializer(run).data, status=status.HTTP_201_CREATED)
