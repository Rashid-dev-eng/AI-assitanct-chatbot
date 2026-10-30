from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from chatbot.authentication import DemoPrincipal
from chatbot.models import LexiconEntry
from chatbot.services.responses import generate_answer


class ConversationalRoutingTests(TestCase):
    def setUp(self):
        self.preview_user = type("PreviewUser", (), {
            "pk": "preview", "username": "demo-student", "role": "preview",
            "is_authenticated": True, "is_staff": False, "is_superuser": False,
        })()

    @override_settings(LLM_API_KEY="", LLM_MODEL="", EMBEDDING_MODEL="")
    def test_greeting_gets_a_greeting_instead_of_a_menu_clarification(self):
        answer = generate_answer("hello", "en", self.preview_user)
        self.assertEqual(answer.source, "conversation")
        self.assertIn("Hi!", answer.message)
        self.assertNotIn("Which DeLMS section", answer.message)

    @override_settings(LLM_API_KEY="", LLM_MODEL="", EMBEDDING_MODEL="")
    def test_misspelled_material_question_gets_a_topic_specific_response(self):
        answer = generate_answer("how to get learnig material", "en", self.preview_user)
        self.assertEqual(answer.intent, "materials")
        self.assertIn("looking for learning materials", answer.message)
        self.assertIn("course", answer.message)

    @override_settings(LLM_API_KEY="", LLM_MODEL="", EMBEDDING_MODEL="")
    def test_submission_how_to_is_not_misreported_as_a_live_record_lookup(self):
        answer = generate_answer("How do I submit an assignment?", "en", self.preview_user)
        self.assertEqual(answer.intent, "assignment")
        self.assertEqual(answer.source, "conversation")
        self.assertIn("What page are you on now?", answer.message)
        self.assertNotIn("Live DeLMS records are not connected", answer.message)

    @override_settings(LLM_API_KEY="", LLM_MODEL="", EMBEDDING_MODEL="")
    def test_explicit_personal_grade_request_keeps_private_record_boundary(self):
        LexiconEntry.objects.create(
            canonical="Grades", language="en", synonyms=["marks"], intent="grade_access",
            service_area="grades", provenance="test fixture", verification_status=LexiconEntry.Verification.SYNTHETIC,
        )
        answer = generate_answer("Show me my grades", "en", self.preview_user)
        self.assertIn("Live DeLMS records are not connected", answer.message)
        self.assertEqual(answer.intent, "grade_access")

    def test_chat_api_handles_greeting_and_unmatched_typo_without_lexicon_gate(self):
        client = APIClient()
        client.force_authenticate(user=DemoPrincipal(pk="demo-student"))
        cases = [
            ("hello", "Hi!"),
            ("how to get learnig material", "looking for learning materials"),
            ("How do I submit an assignment?", "What page are you on now?"),
            ("Where is my quiz?", "open the Quizzes area"),
            ("courses", "enrolled courses"),
        ]
        for question, expected in cases:
            response = client.post("/api/v1/chat/messages/", {
                "message": question, "language": "en", "queryLanguage": "mixed",
            }, format="json")
            self.assertEqual(response.status_code, 201, question)
            self.assertIn(expected.casefold(), response.data["message"].casefold(), question)

    def test_capability_and_short_followups_use_recent_conversation(self):
        client = APIClient()
        client.force_authenticate(user=DemoPrincipal(pk="demo-student"))
        conversation_id = None
        expected = ["Hi!", "I can chat with you", "Yes, I’m here", "explain a DeLMS label"]
        for question, expected_text in zip(("hello", "which services you have", "sure?", "what else"), expected):
            payload = {"message": question, "language": "en"}
            if conversation_id:
                payload["conversationId"] = conversation_id
            response = client.post("/api/v1/chat/messages/", payload, format="json")
            self.assertEqual(response.status_code, 201)
            conversation_id = response.data["conversationId"]
            self.assertIn(expected_text.casefold(), response.data["message"].casefold())

    @override_settings(LLM_API_KEY="configured", LLM_MODEL="test-model", EMBEDDING_MODEL="")
    def test_general_question_can_use_llm_without_fake_knowledge_sources(self):
        from unittest.mock import patch

        with patch("chatbot.services.agent.chat_completion", return_value={"content": "Two plus two is four."}):
            answer = generate_answer("What is two plus two?", "en", self.preview_user)
        self.assertEqual(answer.source, "llm")
        self.assertEqual(answer.response_mode, "llm_general_chat")
        self.assertEqual(answer.source_references, [])
        self.assertEqual(answer.message, "Two plus two is four.")
