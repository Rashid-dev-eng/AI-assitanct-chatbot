from django.urls import path

from chatbot.views import (
    ChatMessageView,
    ConversationDetailView,
    ConversationListView,
    EvaluationCasesView,
    EvaluationRunsView,
    FeedbackView,
    HealthView,
    IntegrationStatusView,
    KnowledgeSearchView,
    LexiconView,
    LexiconInterpretView,
    KnowledgeStatusView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("knowledge/status/", KnowledgeStatusView.as_view(), name="knowledge-status"),
    path("integration/status/", IntegrationStatusView.as_view(), name="integration-status"),
    path("chat/messages/", ChatMessageView.as_view(), name="chat-message"),
    path("chat/conversations/", ConversationListView.as_view(), name="conversation-list"),
    path("chat/conversations/<uuid:conversation_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("feedback/", FeedbackView.as_view(), name="feedback"),
    path("knowledge/search/", KnowledgeSearchView.as_view(), name="knowledge-search"),
    path("lexicon/", LexiconView.as_view(), name="lexicon"),
    path("lexicon/interpret/", LexiconInterpretView.as_view(), name="lexicon-interpret"),
    path("evaluation/cases/", EvaluationCasesView.as_view(), name="evaluation-cases"),
    path("evaluation/runs/", EvaluationRunsView.as_view(), name="evaluation-runs"),
]
