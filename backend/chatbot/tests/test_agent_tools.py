from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from chatbot.models import KnowledgeChunk, KnowledgeDocument
from chatbot.services.agent import run_agent
from chatbot.services.llm import ProviderUnavailable
from chatbot.services.tool_registry import ToolContext, available_tools, execute_tool, openai_tool_definitions


class AgentToolTests(TestCase):
    def setUp(self):
        self.user = type("PreviewUser", (), {
            "pk": "preview-1", "username": "preview-visitor", "role": "preview",
            "is_authenticated": True, "is_staff": False, "is_superuser": False,
        })()

    def test_registry_exposes_only_safe_read_only_tools(self):
        specs = available_tools(self.user)
        names = {tool.name for tool in specs}
        self.assertEqual(names, {"search_delms_knowledge", "get_delms_integration_status"})
        self.assertTrue(all(tool.read_only and tool.retries == 0 for tool in specs))
        self.assertFalse(any("grades" in name or "create" in name for name in names))
        self.assertEqual(len(openai_tool_definitions(self.user)), 2)

    @override_settings(LLM_API_KEY="", LLM_MODEL="", EMBEDDING_MODEL="")
    def test_tool_arguments_cannot_set_role_or_user_id(self):
        context = ToolContext(self.user, "preview-1", "preview")
        result = execute_tool("search_delms_knowledge", {"query": "marks", "role": "administrator", "user_id": 3}, context)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "Tool arguments were invalid.")

    def test_user_selected_interface_does_not_change_trusted_tool_role(self):
        from chatbot.services.tool_registry import trusted_role
        self.assertEqual(trusted_role(self.user), "unknown")
        # The request's interface_context is intentionally not part of ToolContext.
        context = ToolContext(self.user, "preview-1", trusted_role(self.user))
        self.assertEqual(context.trusted_role, "unknown")

    def test_integration_status_tool_is_local_and_never_claims_live_access(self):
        context = ToolContext(self.user, "preview-1", "unknown")
        result = execute_tool("get_delms_integration_status", {}, context)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["status"], "disabled")
        self.assertFalse(result["data"]["liveDataAccess"])

    @override_settings(LLM_API_KEY="configured", LLM_MODEL="test-model", EMBEDDING_MODEL="")
    @patch("chatbot.services.agent.chat_completion")
    def test_llm_tool_call_executes_reviewed_search_and_returns_source(self, completion):
        document = KnowledgeDocument.objects.create(
            title="Communication overview", body="Communication includes the reviewed Messages and Notifications labels.",
            source_file="communication.md", language="en", provenance="Approved source text.",
            verification_status=KnowledgeDocument.Verification.VERIFIED, reviewer="reviewer", reviewed_at=timezone.now(),
        )
        KnowledgeChunk.objects.create(
            document=document, ordinal=0, title=document.title, body=document.body,
            source_section="Communication", language="en", source_type="md", document_version="1",
            content_hash="b" * 64,
        )
        completion.side_effect = [
            {"tool_calls": [{"id": "call-1", "function": {"name": "search_delms_knowledge", "arguments": '{"query":"communication notifications","language":"en"}'}}]},
            {"content": "The source groups Messages and Notifications under Communication [1]."},
        ]
        answer = run_agent("Where are notifications?", "en", self.user)
        self.assertEqual(completion.call_count, 2)
        self.assertIn("[1]", answer["answer"])
        self.assertEqual(answer["sources"][0]["sourceFile"], "communication.md")
        self.assertEqual(answer["toolsUsed"], ["search_delms_knowledge"])

    @override_settings(LLM_API_KEY="configured", LLM_MODEL="test-model")
    @patch("chatbot.services.agent.chat_completion")
    def test_agent_rejects_unknown_personal_data_tool(self, completion):
        completion.side_effect = [
            {"tool_calls": [{"id": "call-1", "function": {"name": "get_my_grades", "arguments": "{}"}}]},
            {"content": "Your grades are A [1]."},
        ]
        with self.assertRaises(ProviderUnavailable):
            run_agent("Show my grades", "en", self.user)
        self.assertFalse(any(spec.name == "get_my_grades" for spec in available_tools(self.user)))
