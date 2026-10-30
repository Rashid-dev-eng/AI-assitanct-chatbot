import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from chatbot.models import ChatMessage, Conversation, EvaluationCase, KnowledgeDocument, LexiconEntry, LexiconRevision


@override_settings(DEBUG=True, DEMO_AUTH_MODE=True, REST_FRAMEWORK={
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "chatbot.authentication.DevelopmentDemoAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "chatbot.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [],
})
class ChatApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_data", verbosity=0)

    def setUp(self):
        self.client = APIClient()

    def post_chat(self, message="Where do I find my courses?", **extra):
        return self.client.post("/api/v1/chat/messages/", {"message": message, "language": "en", **extra}, format="json")

    def test_frontend_contract_and_contextual_course_response(self):
        response = self.post_chat(message="My Courses")
        self.assertEqual(response.status_code, 201)
        self.assertIn("conversationId", response.data)
        self.assertEqual(response.data["source"], "conversation")
        self.assertEqual(response.data["intent"], "courses")
        self.assertIn("enrolled courses", response.data["message"])
        self.assertEqual(response.data["sourceReferences"], [])

    def test_camel_case_conversation_id_preserves_context(self):
        first = self.post_chat()
        conversation_id = first.data["conversationId"]
        second = self.client.post("/api/v1/chat/messages/", {
            "message": "Where do I find my courses?", "language": "en", "conversationId": conversation_id,
        }, format="json")
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data["conversationId"], conversation_id)
        self.assertEqual(ChatMessage.objects.filter(conversation_id=conversation_id).count(), 4)

    def test_snake_case_alias_is_accepted_for_non_frontend_clients(self):
        first = self.post_chat()
        second = self.client.post("/api/v1/chat/messages/", {
            "message": "Where do I find my courses?", "language": "en", "conversation_id": first.data["conversationId"],
        }, format="json")
        self.assertEqual(second.status_code, 201)

    def test_client_cannot_choose_an_identity_using_headers(self):
        self.client.credentials(HTTP_X_DEMO_USER="admin", HTTP_X_DEMO_ROLE="administrator")
        response = self.client.get("/api/v1/lexicon/")
        self.assertEqual(response.status_code, 403)

    def test_conversation_is_private_to_server_authenticated_owner(self):
        created = self.post_chat()
        conversation_id = created.data["conversationId"]
        with override_settings(DEMO_AUTH_USER_ID="another-fixed-demo-user"):
            response = self.client.get(f"/api/v1/chat/conversations/{conversation_id}/")
        self.assertEqual(response.status_code, 404)

    def test_list_and_delete_only_return_own_conversations(self):
        created = self.post_chat()
        conversation_id = created.data["conversationId"]
        listed = self.client.get("/api/v1/chat/conversations/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)
        deleted = self.client.delete(f"/api/v1/chat/conversations/{conversation_id}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(Conversation.objects.filter(pk=conversation_id).exists())

    def test_live_grades_are_never_fabricated_in_demo_mode(self):
        response = self.post_chat("Where are my grades?")
        self.assertEqual(response.status_code, 201)
        self.assertIn("no DMI records", response.data["message"])
        self.assertEqual(response.data["integrationStatus"], "disabled")

    def test_integration_status_does_not_expose_token_or_url(self):
        with override_settings(MOODLE_ENABLED=True, MOODLE_REST_URL="https://moodle.invalid/webservice/rest/server.php", MOODLE_SERVICE_TOKEN="do-not-return-this", MOODLE_FUNCTIONS_JSON='{"site_info":"core_webservice_get_site_info"}'):
            response = self.client.get("/api/v1/integration/status/")
        self.assertEqual(response.status_code, 200)
        serialized = str(response.data)
        self.assertNotIn("do-not-return-this", serialized)
        self.assertNotIn("moodle.invalid", serialized)
        self.assertEqual(response.data["status"], "configured_unverified")

    def test_health_is_available_without_authentication(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")

    def test_knowledge_search_excludes_synthetic_and_unreviewed_records(self):
        KnowledgeDocument.objects.create(title="Synthetic", body="course navigation demo", language="en", provenance="test", verification_status="synthetic")
        KnowledgeDocument.objects.create(title="Unreviewed", body="course navigation info", language="en", provenance="test", verification_status="verified")
        KnowledgeDocument.objects.create(title="Approved", body="course navigation guide", language="en", provenance="test", source_file="test.md", reviewer="reviewer", verification_status="verified", reviewed_at=__import__("django.utils.timezone", fromlist=["now"]).now())
        response = self.client.get("/api/v1/knowledge/search/", {"q": "course navigation", "language": "en"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["title"] for item in response.data], ["Approved"])

    def test_lexicon_endpoint_requires_staff(self):
        response = self.client.get("/api/v1/lexicon/")
        self.assertEqual(response.status_code, 403)

    def test_staff_lexicon_view_includes_provenance_and_review_status(self):
        entry = LexiconEntry.objects.get(canonical="Grades", language="en", intent="grade_access")
        staff = get_user_model().objects.create_user(username=f"lexicon-{uuid.uuid4().hex[:8]}", password="test-only", is_staff=True)
        staff_client = APIClient()
        staff_client.force_authenticate(user=staff)
        response = staff_client.get("/api/v1/lexicon/")
        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.data if item["id"] == str(entry.pk))
        self.assertEqual(row["sourceReference"], "src/data/courses.ts")
        self.assertEqual(row["translationStatus"], "proposed")
        self.assertIsNone(row["reviewedAt"])

    def test_service_interpretation_is_separate_from_answer_retrieval(self):
        response = self.client.post("/api/v1/lexicon/interpret/", {
            "query": "Ninawezaje kuona matokeo yangu?", "language": "sw", "request_type": "service",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "grade_access")
        self.assertEqual(response.data["serviceArea"], "grades")
        self.assertEqual(response.data["retrieval"], "separate_step_required")
        self.assertEqual(response.data["translationStatus"], "proposed")

    def test_translation_lookup_does_not_invent_a_missing_equivalent(self):
        response = self.client.post("/api/v1/lexicon/interpret/", {
            "query": "Grades", "language": "en", "request_type": "translation", "target_language": "sw",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["translation"], "")
        self.assertIn(response.data["translationStatus"], {"proposed", "missing"})

    def test_openapi_schema_is_available(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)


@override_settings(DEBUG=True, DEMO_AUTH_MODE=True, REST_FRAMEWORK={
    "DEFAULT_AUTHENTICATION_CLASSES": ["chatbot.authentication.DevelopmentDemoAuthentication", "rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "chatbot.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [],
})
class AdminResearchApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = get_user_model().objects.create_user(username=f"research-{uuid.uuid4().hex[:8]}", password="test-only", is_staff=True, is_active=True)
        self.client.force_authenticate(user=self.staff)

    def test_evaluation_endpoint_computes_separate_intent_and_response_metrics(self):
        case = EvaluationCase.objects.create(query="test question", language="en", intended_intent="course_navigation", expected_service_area="courses", dataset_label="unit-test", is_synthetic=True)
        response = self.client.post("/api/v1/evaluation/runs/", {
            "evaluation_version": "baseline-v1",
            "dataset_label": "unit-test",
            "results": [{"case_id": str(case.pk), "predicted_intent": "course_navigation", "predicted_service_area": "courses", "response_correct": False}],
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["metrics"]["queryInterpretationAccuracy"], 1.0)
        self.assertEqual(response.data["metrics"]["serviceMappingAccuracy"], 1.0)
        self.assertEqual(response.data["metrics"]["responseCorrectness"], 0.0)

    def test_evaluation_tracks_translation_and_clarification_separately(self):
        service = EvaluationCase.objects.create(query="grades", language="en", intended_intent="grade_access", expected_service_area="grades", dataset_label="multi-metric", is_synthetic=True)
        translation = EvaluationCase.objects.create(query="translate grades", language="en", intended_intent="translation_lookup", request_type="translation", dataset_label="multi-metric", is_synthetic=True)
        clarification = EvaluationCase.objects.create(query="what status", language="en", intended_intent="unknown", request_type="clarification", expects_clarification=True, dataset_label="multi-metric", is_synthetic=True)
        response = self.client.post("/api/v1/evaluation/runs/", {
            "evaluation_version": "bilingual-v1",
            "dataset_label": "multi-metric",
            "results": [
                {"case_id": str(service.pk), "predicted_intent": "grade_access", "predicted_service_area": "grades", "response_correct": True},
                {"case_id": str(translation.pk), "predicted_intent": "translation_lookup", "predicted_service_area": "", "response_correct": True, "translation_correct": True},
                {"case_id": str(clarification.pk), "predicted_intent": "unknown", "predicted_service_area": "", "response_correct": True, "clarification_appropriate": True},
            ],
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["metrics"]["queryInterpretationAccuracy"], 1.0)
        self.assertEqual(response.data["metrics"]["serviceMappingAccuracy"], 1.0)
        self.assertEqual(response.data["metrics"]["responseCorrectness"], 1.0)
        self.assertEqual(response.data["metrics"]["translationQuality"], 1.0)
        self.assertEqual(response.data["metrics"]["clarificationAppropriateness"], 1.0)

    def test_staff_account_is_available_for_lexicon_administration(self):
        self.assertTrue(self.staff.is_staff)

    def test_verified_translation_requires_reviewer_source_and_date(self):
        entry = LexiconEntry(
            canonical="Grades", language="en", intent="grade_access",
            provenance="test source", swahili_equivalent="", translation_status="verified",
        )
        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_json_import_rejects_duplicate_and_records_update_history(self):
        fixture = Path(__file__).parent / "fixtures" / "lexicon_import_valid.json"
        call_command("import_lexicon", str(fixture), verbosity=0)
        entry = LexiconEntry.objects.get(canonical="Import fixture term")
        self.assertEqual(entry.translation_status, LexiconEntry.TranslationStatus.MISSING)
        self.assertEqual(LexiconRevision.objects.filter(entry=entry).count(), 1)
        with self.assertRaises(CommandError):
            call_command("import_lexicon", str(fixture), verbosity=0)
        call_command("import_lexicon", str(fixture), "--update-existing", "--change-note", "test update", "--changed-by", self.staff.username, verbosity=0)
        revisions = LexiconRevision.objects.filter(entry=entry).order_by("version")
        self.assertEqual(list(revisions.values_list("version", flat=True)), [1, 2])
        self.assertEqual(revisions.last().changed_by, self.staff)

    def test_csv_template_import_is_supported(self):
        template = Path(__file__).resolve().parents[2] / "data" / "lexicon_import_template.csv"
        call_command("import_lexicon", str(template), "--update-existing", "--change-note", "CSV importer test", verbosity=0)
        entry = LexiconEntry.objects.get(canonical="Grades", intent="grade_access", language="en")
        self.assertTrue(entry.revisions.exists())

    def test_full_initial_dataset_import_validates_all_source_rows(self):
        call_command("seed_demo_data", verbosity=0)
        source = Path(__file__).resolve().parents[2] / "data" / "lexicon_initial.json"
        call_command("import_lexicon", str(source), "--update-existing", "--change-note", "validate initial dataset", verbosity=0)
        self.assertEqual(LexiconEntry.objects.filter(is_active=True, language="en").count(), 42)
