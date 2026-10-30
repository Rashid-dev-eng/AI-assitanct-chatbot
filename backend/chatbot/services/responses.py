from dataclasses import dataclass

from django.conf import settings

from chatbot.models import LexiconEntry
from chatbot.services.agent import run_agent
from chatbot.services.knowledge import retrieve_knowledge
from chatbot.services.llm import ProviderUnavailable
from chatbot.services.conversation import contextual_fallback, guidance_reply, guidance_topic, is_personal_record_request, resolve_course_followup, small_talk_reply
from chatbot.services.semantic import IntentMatch, detect_response_language, match_intent
from chatbot.services.tool_registry import trusted_role

LIVE_DATA_INTENTS = {"course_lookup", "assignment_status", "quiz_status", "grade_access"}

COPY = {
    "en": {
        "clarify": "I’m not sure which task you mean. Are you trying to find a course, open learning materials, submit an assignment, find a quiz, or view grade guidance?",
        "unavailable": "Live DeLMS records are not connected in this environment. This answer contains no DMI records. Please contact DMI ICT to enable an authorized integration.",
        "fallback": "I can help with DeLMS navigation, courses, learning materials, assignments, quizzes, and grade guidance. I don’t have reviewed directions or live records for that request yet. What are you trying to do?",
        "unverified_guidance": "I recognized that section in this project’s prototype, but reviewed DMI navigation instructions for it are not available yet.",
    },
    "sw": {
        "clarify": "Sijaelewa unamaanisha kazi gani. Unatafuta kozi, vifaa vya kujifunzia, kuwasilisha kazi, kutafuta jaribio au maelekezo ya alama?",
        "unavailable": "Taarifa za moja kwa moja za DeLMS hazijaunganishwa katika mazingira haya. Jibu hili halina rekodi za DMI. Wasiliana na kitengo cha TEHAMA cha DMI ili kuwezesha muunganisho ulioidhinishwa.",
        "fallback": "Ninaweza kusaidia kuelekeza matumizi ya DeLMS, kozi, vifaa vya kujifunzia, kazi, majaribio na maelekezo ya alama. Bado sina maelekezo yaliyokaguliwa au rekodi za moja kwa moja za ombi hilo. Unajaribu kufanya nini?",
        "unverified_guidance": "Nimetambua sehemu hiyo katika mfano wa mradi huu, lakini bado hakuna maelekezo ya urambazaji ya DMI yaliyokaguliwa.",
    },
}


@dataclass
class Answer:
    message: str
    language: str
    source: str
    intent: str | None
    confidence: float | None
    needs_clarification: bool
    source_references: list[dict]
    integration_status: str
    related_questions: list[str]
    retrieval_status: str = "not_attempted"
    response_mode: str = "fallback"


def _role(user) -> str:
    return trusted_role(user)


def _retrieved_fallback(query: str, language: str, role: str) -> Answer | None:
    ranked = retrieve_knowledge(query, language, role, limit=5)
    if not ranked or ranked[0][0] < 0.35:
        return None
    chunk = ranked[0][1]
    source_refs = [{"title": item.title, "url": item.document.source_url or None, "verificationStatus": "verified", "sourceFile": item.document.source_file, "section": item.source_section, "score": round(score, 3)} for score, item in ranked]
    return Answer(
        message=chunk.body,
        language=language,
        source="knowledge",
        intent="institutional_knowledge",
        confidence=round(ranked[0][0], 3),
        needs_clarification=False,
        source_references=source_refs,
        integration_status="disabled" if not settings.MOODLE_ENABLED else "configured",
        related_questions=[],
        retrieval_status="matched",
        response_mode="retrieval_fallback",
    )


def _tool_agent_answer(query: str, language: str, user, context: list[str] | None, interface_context: str, interpretation: dict | None, general_chat: bool = False) -> Answer | None:
    try:
        result = run_agent(query, language, user, context or [], interface_context, interpretation, general_chat)
    except ProviderUnavailable:
        return None
    if not result["sources"] and not general_chat:
        return None
    return Answer(
        message=result["answer"],
        language=language,
        source="llm",
        intent="general_conversation" if general_chat else "tool_augmented_answer",
        confidence=None,
        needs_clarification=False,
        source_references=result["sources"],
        integration_status="disabled" if not settings.MOODLE_ENABLED else "configured",
        related_questions=[],
        retrieval_status="tool_results" if result["sources"] else "not_required",
        response_mode="llm_general_chat" if general_chat and not result["sources"] else "tool_agent",
    )


def generate_answer(query: str, requested_language: str, user, query_language: str | None = None, context: list[str] | None = None, interface_context: str | None = None) -> Answer:
    language = detect_response_language(requested_language, query)
    copy = COPY[language]
    greeting = small_talk_reply(query, language, context)
    if greeting:
        return Answer(greeting, language, "conversation", "small_talk", 1.0, False, [], "disabled", [], "not_attempted", "conversation")
    role = _role(user)
    match: IntentMatch | None = match_intent(query, query_language or language, role)
    course_followup = resolve_course_followup(query, context)
    topic = "courses" if course_followup else guidance_topic(query)
    interpretation = None
    if match:
        interpretation = {
            "intent": match.entry.intent,
            "serviceArea": match.entry.service_area or match.entry.domain,
            "canonicalTerm": match.entry.canonical,
            "confidence": round(match.confidence, 3),
            "verificationStatus": match.entry.verification_status,
        }
        if match.ambiguous or match.confidence < match.entry.confidence_threshold:
            return Answer(copy["clarify"], language, "mock", match.entry.intent, round(match.confidence, 3), True, [], "disabled", [], "ambiguous_intent", "clarification")
    if settings.LLM_API_KEY and settings.LLM_MODEL:
        tool_answer = _tool_agent_answer(query, language, user, context, interface_context or "unspecified", interpretation, general_chat=not match and not topic)
        if tool_answer:
            return tool_answer
    query_for_retrieval = f"{query} {course_followup['search_query']}" if course_followup else query
    if interface_context in {"student", "teacher", "administrator"}:
        query_for_retrieval = f"{interface_context} interface {query_for_retrieval}"
    knowledge_answer = _retrieved_fallback(query_for_retrieval, language, role)
    if knowledge_answer:
        return knowledge_answer

    if topic:
        if is_personal_record_request(query, match.entry.intent if match else None):
            return Answer(copy["unavailable"], language, "mock", match.entry.intent if match else topic, None, False, [], "disabled", [], "api_unavailable", "fallback")
        return Answer(guidance_reply(topic, language, query, course_followup["choice"] if course_followup else None), language, "conversation", topic, match.confidence if match else None, True, [], "disabled", [], "source_missing", "clarification")

    if not match:
        contextual = contextual_fallback(query, language, context)
        if contextual:
            return Answer(contextual, language, "conversation", "follow_up", None, False, [], "disabled", [], "contextual", "conversation")
        return Answer(copy["fallback"], language, "mock", None, None, True, [], "disabled", [], "no_match", "fallback")
    entry = match.entry
    if match.ambiguous or match.confidence < entry.confidence_threshold:
        return Answer(copy["clarify"], language, "mock", entry.intent, round(match.confidence, 3), True, [], "disabled", [], "below_threshold", "fallback")

    if entry.verification_status == LexiconEntry.Verification.VERIFIED:
        if entry.reviewed_at and entry.response_text.strip():
            return Answer(
                entry.response_text,
                language,
                "api",
                entry.intent,
                round(match.confidence, 3),
                False,
                [{"title": entry.source_reference or entry.canonical, "url": None, "verificationStatus": "verified"}],
                "disabled" if not settings.MOODLE_ENABLED else "configured",
                [],
            )
        return Answer(copy["fallback"], language, "mock", entry.intent, round(match.confidence, 3), True, [], "disabled", [])

    if entry.intent in LIVE_DATA_INTENTS:
        return Answer(copy["unavailable"], language, "mock", entry.intent, round(match.confidence, 3), False, [], "disabled", [])

    if not entry.response_text.strip():
        return Answer(copy["unverified_guidance"], language, "mock", entry.intent, round(match.confidence, 3), False, [], "disabled", [])

    return Answer(
        entry.response_text,
        language,
        "mock",
        entry.intent,
        round(match.confidence, 3),
        False,
        [{"title": "Synthetic development example (not official DMI guidance)", "url": None, "verificationStatus": "synthetic"}],
        "disabled",
        [],
    )
