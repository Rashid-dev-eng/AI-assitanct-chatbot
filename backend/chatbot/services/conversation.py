"""Small, predictable conversational routing for common non-RAG turns."""
import re
from difflib import SequenceMatcher

from chatbot.services.normalization import normalize_text, tokens


SMALL_TALK = {
    "en": {
        "greeting": "Hi! Nice to meet you. What would you like to talk about? I can also help with DeLMS questions when reviewed guidance is available.",
        "thanks": "You’re welcome! What would you like help finding in DeLMS?",
        "identity": "I’m the DMI DeLMS Assistant. I can chat with you and help with DeLMS questions. I can’t access live courses, grades, or account records in this preview.",
        "capabilities": "I can chat with you, explain DeLMS terms, and help with courses, learning materials, assignments, quizzes, and grade-page guidance when reviewed instructions are available. Detailed answers on general topics may be limited right now. I can’t check live deadlines, submissions, enrollments, or personal marks here. What would you like to ask?",
        "more": "You can ask me to explain a DeLMS label, help interpret instructions you paste from a page, or talk about a general topic. For exact DMI navigation, I need reviewed source material; for personal records, an authorized live connection is required.",
        "sure": "Yes, I’m here. We can talk about DeLMS or another topic. If I don’t know something, I’ll say so instead of making it up. What would you like to discuss?",
        "ack": "Got it. What would you like to do next?",
        "how_are_you": "I’m doing well, thanks for asking. How are you?",
        "unclear_followup": "I may have missed what you meant. Are you asking about the last thing we discussed, or would you like to start a new topic?",
        "unclear_followup_again": "Sorry, I still don’t have enough detail to answer. Could you rephrase that or name the DeLMS page or task you mean?",
    },
    "sw": {
        "greeting": "Habari! Nimefurahi kukutana nawe. Ungependa tuzungumzie nini? Ninaweza pia kusaidia kuhusu DeLMS pale maelekezo yaliyokaguliwa yanapopatikana.",
        "thanks": "Karibu! Ungependa nikusaidie kupata nini kwenye DeLMS?",
        "identity": "Mimi ni DMI DeLMS Assistant. Ninaweza kuzungumza nawe na kusaidia kuhusu DeLMS. Katika toleo hili siwezi kufikia kozi, alama au rekodi binafsi za moja kwa moja.",
        "capabilities": "Ninaweza kuzungumza nawe kwa kawaida, kueleza istilahi za DeLMS na kusaidia kuhusu kozi, vifaa vya kujifunzia, kazi, majaribio na maelekezo ya ukurasa wa alama pale maelekezo yaliyokaguliwa yanapopatikana. Siwezi kuangalia tarehe za mwisho, kazi zilizowasilishwa, usajili au alama binafsi za moja kwa moja. Unaweza kuuliza swali la jumla au kuniambia unachojaribu kufanya.",
        "more": "Unaweza kuniomba nieleze jina la sehemu ya DeLMS, nikusaidie kuelewa maelekezo utakayonakili kutoka kwenye ukurasa, au tuzungumzie mada ya jumla. Kwa maelekezo halisi ya DMI nahitaji chanzo kilichokaguliwa; kwa rekodi binafsi nahitaji muunganisho ulioidhinishwa.",
        "sure": "Ndiyo, nipo hapa. Tunaweza kuzungumzia DeLMS au mada nyingine. Nisipojua jambo, nitasema badala ya kubuni jibu. Ungependa tuzungumzie nini?",
        "ack": "Sawa. Ungependa kufanya nini sasa?",
        "how_are_you": "Niko vizuri, asante kwa kuuliza. Wewe je?",
        "unclear_followup": "Huenda sikuelewa ulichomaanisha. Unaulizia tulichokuwa tunazungumzia au ungependa kuanza mada mpya?",
        "unclear_followup_again": "Samahani, bado sijapata maelezo ya kutosha kujibu. Tafadhali fafanua au taja ukurasa au kazi ya DeLMS unayomaanisha.",
    },
}

GUIDANCE_NOT_LOADED = {
    "en": {
        "materials": "I understand you’re looking for learning materials. I don’t yet have reviewed DMI instructions or course records to point you to. Which course or course code are you asking about?",
        "assignment": "I understand you want help with an assignment. I don’t yet have reviewed DMI instructions for the submission steps. Are you asking how to upload your work, or whether a submission was received?",
        "quiz": "Are you trying to open the Quizzes area, find a particular quiz, or check a quiz result? I don’t have reviewed course-specific quiz instructions or live quiz records in this preview.",
        "courses": "Are you looking for your enrolled courses or browsing the course catalogue? I don’t have a live course list in this preview.",
        "grades": "I can help with grade-page navigation when reviewed instructions are available, but I can’t retrieve personal marks here. Are you asking where to view grades or asking about a specific result?",
    },
    "sw": {
        "materials": "Nimeelewa unatafuta vifaa vya kujifunzia. Bado sina maelekezo ya DMI yaliyokaguliwa au rekodi za kozi za kukuonyesha mahali. Unaulizia kozi gani au msimbo gani wa kozi?",
        "assignment": "Nimeelewa unahitaji msaada kuhusu kazi. Bado sina maelekezo ya DMI yaliyokaguliwa kuhusu hatua za kuwasilisha. Unauliza jinsi ya kupakia kazi au kama ilipokelewa?",
        "quiz": "Unajaribu kufungua sehemu ya Quizzes, kutafuta jaribio maalum, au kuangalia matokeo? Sina maelekezo ya kozi yaliyokaguliwa wala rekodi za majaribio za moja kwa moja katika toleo hili.",
        "courses": "Unatafuta kozi ulizojiandikisha au unavinjari orodha ya kozi? Sina orodha ya moja kwa moja ya kozi katika toleo hili.",
        "grades": "Ninaweza kusaidia kuelekeza ukurasa wa alama yakipatikana maelekezo yaliyokaguliwa, lakini siwezi kupata alama binafsi hapa. Unauliza mahali pa kuona alama au unaulizia matokeo maalum?",
    },
}


def guidance_reply(topic: str, language: str, query: str, course_choice: str | None = None) -> str:
    if topic == "courses" and course_choice == "enrolled":
        return "Got it—you mean courses enrolled to your account. I searched the reviewed DeLMS sources available here, but they don’t include your personal course list, and this preview isn’t connected to live DeLMS. I can’t retrieve your enrolled courses here."
    if topic == "courses" and course_choice == "catalogue":
        return "Got it—you mean the course catalogue. I searched the reviewed sources available here, but no official course catalogue is available, so I can’t reliably list the current DMI courses. Share an official catalogue or course guide and I can search it."
    if topic == "assignment" and language == "en" and re.search(r"\b(how|steps?|submit|upload|turn in)\b", normalize_text(query)):
        return "You’re asking how to submit an assignment. I don’t have reviewed DMI instructions to verify the exact steps. What page are you on now? I can help interpret the instructions or buttons you see there."
    if topic == "assignment" and language == "sw" and re.search(r"\b(jinsi|wasilisha|kupakia)\b", normalize_text(query)):
        return "Unauliza jinsi ya kuwasilisha kazi. Sina maelekezo ya DMI yaliyokaguliwa ya kuthibitisha hatua halisi. Uko kwenye ukurasa gani sasa? Ninaweza kusaidia kueleza maelekezo au vitufe unavyoona."
    return GUIDANCE_NOT_LOADED[language][topic]


def small_talk_reply(query: str, language: str, context: list[str] | None = None) -> str | None:
    text = normalize_text(query).strip()
    history = normalize_text(" ".join((context or [])[-4:]))
    if re.fullmatch(r"(?:hi|hello|hey|hiya|good morning|good afternoon|good evening|habari|hujambo|mambo|salama)(?: there)?", text):
        return SMALL_TALK[language]["greeting"]
    if re.fullmatch(r"(?:thanks|thank you|thx|asante|asanteni|ahsante)(?: very much)?", text):
        return SMALL_TALK[language]["thanks"]
    if text in {"who are you", "wewe ni nani"}:
        return SMALL_TALK[language]["identity"]
    if text in {"what can you do", "what can you help me with", "what can you help with", "which services do you have", "which services you have", "what services do you offer", "what services you have", "unaweza kusaidia nini", "una huduma gani"} or (re.search(r"\b(services|capabilities)\b", text) and re.search(r"\b(what|which|do|offer|have)\b", text)):
        return SMALL_TALK[language]["capabilities"]
    if re.search(r"\bservices?\b", text) and re.search(r"\b(any|some|available|there|have|offer|provide)\b", text):
        return SMALL_TALK[language]["capabilities"]
    if text in {"how are you", "how are you doing", "ukoje", "habari yako"}:
        return SMALL_TALK[language]["how_are_you"]
    if text in {"what else", "anything else", "what more", "nini kingine"}:
        return SMALL_TALK[language]["more"]
    if text in {"sure", "sure?", "really", "are you sure", "is that so", "kweli", "una uhakika"}:
        return SMALL_TALK[language]["sure"] if history else SMALL_TALK[language]["ack"]
    if text in {"ok", "okay", "alright", "got it", "sawa", "ndiyo", "yes"}:
        return SMALL_TALK[language]["ack"]
    return None


def contextual_fallback(query: str, language: str, context: list[str] | None = None) -> str | None:
    if context:
        history = normalize_text(" ".join(context[-4:]))
        repeated_clarification = normalize_text(SMALL_TALK[language]["unclear_followup"])
        if repeated_clarification in history:
            return SMALL_TALK[language]["unclear_followup_again"]
        return SMALL_TALK[language]["unclear_followup"]
    return None


def resolve_course_followup(query: str, context: list[str] | None = None) -> dict | None:
    """Resolve brief choices after the enrolled-courses/catalogue clarification."""
    history = normalize_text(" ".join((context or [])[-4:]))
    if "enrolled courses or browsing the course catalogue" not in history:
        return None
    text = normalize_text(query)
    words = set(tokens(text))
    if words & {"enrolled", "enrolment", "enrollment", "registered", "registration", "registrations"} or "my courses" in text:
        return {"choice": "enrolled", "search_query": "enrolled courses personal course list"}
    if words & {"catalogue", "catalog", "browse", "browsing", "catalogue's"}:
        return {"choice": "catalogue", "search_query": "official course catalogue available courses"}
    return None


def _has_concept(words: set[str], candidates: tuple[str, ...]) -> bool:
    for word in words:
        if any(word == candidate or (len(word) >= 5 and SequenceMatcher(None, word, candidate).ratio() >= 0.80) for candidate in candidates):
            return True
    return False


def guidance_topic(query: str) -> str | None:
    words = set(tokens(normalize_text(query)))
    if _has_concept(words, ("material", "materials", "resource", "resources", "notes", "lecture", "kujifunzia", "nyenzo")):
        return "materials"
    if _has_concept(words, ("assignment", "assignments", "submission", "submit", "upload", "kazi", "wasilisha")):
        return "assignment"
    if _has_concept(words, ("quiz", "quizzes", "test", "tests", "jaribio", "majaribio")):
        return "quiz"
    if _has_concept(words, ("grade", "grades", "mark", "marks", "result", "results", "alama", "matokeo")):
        return "grades"
    if _has_concept(words, ("course", "courses", "kozi", "catalogue", "catalog")):
        return "courses"
    return None


def is_personal_record_request(query: str, intent: str | None) -> bool:
    text = normalize_text(query)
    if intent == "grade_access":
        return bool(re.search(r"\b(show|get|what are|what is|where are|tell me|check)\s+(?:me\s+)?(?:my|the)\s+(?:marks?|grades?|scores?|results?)\b|\bmarks? yangu\b|\balama zangu\b", text))
    if intent == "course_lookup":
        return bool(re.search(r"\b(show|list|get)\s+(?:me\s+)?my courses\b|\bmy enrolled courses\b", text))
    if intent in {"assignment_status", "quiz_status"}:
        return bool(re.search(r"\b(did i submit|has my .* (?:been|arrived)|submission status|my .* (?:score|result|grade)|did i pass)\b", text))
    return False
