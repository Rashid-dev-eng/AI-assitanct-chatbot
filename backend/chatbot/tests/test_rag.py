import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from chatbot.models import KnowledgeChunk, KnowledgeDocument
from chatbot.services.knowledge import retrieve_knowledge
from chatbot.services.responses import generate_answer


class KnowledgeRetrievalTests(TestCase):
    def setUp(self):
        self.document = KnowledgeDocument.objects.create(
            title="Teacher grade report", body="Use the Grader report to review course grades.",
            document_id="teacher-grade-guide", source_file="guide.md", source_section="Grades",
            canonical_topic="grader report", language="en", provenance="Reviewed source for test.",
            allowed_roles=["teacher"], verification_status=KnowledgeDocument.Verification.VERIFIED,
            reviewer="reviewer", reviewed_at=timezone.now(),
        )
        KnowledgeChunk.objects.create(
            document=self.document, ordinal=0, title="Teacher grade report",
            body=self.document.body, source_section="Grades", canonical_topic="grader report",
            interface_role="teacher", language="en", source_type="md", document_version="1",
            content_hash="a" * 64,
        )

    @override_settings(LLM_API_KEY="", LLM_MODEL="", EMBEDDING_MODEL="")
    def test_retrieval_fallback_is_grounded_and_source_cited(self):
        user = type("Teacher", (), {"role": "teacher", "is_staff": False})()
        answer = generate_answer("Where is the grader report?", "en", user, interface_context="teacher")
        self.assertEqual(answer.response_mode, "retrieval_fallback")
        self.assertEqual(answer.message, self.document.body)
        self.assertEqual(answer.source_references[0]["sourceFile"], "guide.md")

    def test_role_restricted_chunks_are_excluded_without_context(self):
        self.assertEqual(retrieve_knowledge("grader report course grades", "en", "preview"), [])
        self.assertEqual(len(retrieve_knowledge("grader report course grades", "en", "teacher")), 1)


class KnowledgeIngestionTests(TestCase):
    @patch("chatbot.management.commands.ingest_knowledge.embed_text", return_value=[])
    def test_ingestion_creates_pending_chunks_and_a_report(self, _embedding):
        with tempfile.TemporaryDirectory() as temp:
            source_dir = Path(temp) / "sources"
            source_dir.mkdir()
            (source_dir / "guide.md").write_text("# Assignments\n\nOpen the Assignments page to view submitted work.", encoding="utf-8")
            call_command("ingest_knowledge", str(source_dir), verbosity=0)
            document = KnowledgeDocument.objects.get(source_file="guide.md")
            chunk = KnowledgeChunk.objects.get(document=document)
            self.assertEqual(document.verification_status, KnowledgeDocument.Verification.PENDING)
            self.assertEqual(chunk.source_section, "Assignments")
            report = (source_dir / "ingestion-report.json").read_text(encoding="utf-8")
            self.assertIn('"chunksCreated": 1', report)

    def test_public_knowledge_status_does_not_require_auth(self):
        response = APIClient().get("/api/v1/knowledge/status/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["verifiedDocuments"], 0)
