from django.core.management import call_command
from django.test import TestCase

from chatbot.models import LexiconEntry
from chatbot.services.normalization import normalize_text
from chatbot.services.semantic import detect_response_language, match_intent


class NormalizationTests(TestCase):
    def test_unicode_and_spacing_are_normalized(self):
        self.assertEqual(normalize_text("  TAFADHALI,  KOZI! "), "tafadhali kozi")

    def test_accented_text_normalizes_conservatively(self):
        self.assertEqual(normalize_text("café"), "cafe")


class SemanticMatchingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_data", verbosity=0)

    def test_source_label_matches_course_service(self):
        match = match_intent("My Courses", "en")
        self.assertIsNotNone(match)
        self.assertEqual(match.entry.intent, "course_navigation")
        self.assertGreaterEqual(match.confidence, 0.60)

    def test_user_provided_swahili_assignment_example_is_unverified_but_interpretable(self):
        match = match_intent("Ninaipata wapi assignment yangu?", "sw")
        self.assertIsNotNone(match)
        self.assertEqual(match.entry.intent, "assignment_status")
        self.assertEqual(match.entry.translation_status, LexiconEntry.TranslationStatus.PROPOSED)

    def test_mixed_language_query_is_supported_conservatively(self):
        query = "Ninaipata wapi assignment yangu?"
        language = detect_response_language("mixed", query)
        match = match_intent(query, "mixed")
        self.assertEqual(language, "sw")
        self.assertIsNotNone(match)
        self.assertEqual(match.entry.intent, "assignment_status")

    def test_user_provided_swahili_material_query_is_detected_as_swahili(self):
        language = detect_response_language("mixed", "Nisaidie kupata vifaa vya kujifunzia.")
        self.assertEqual(language, "sw")
        match = match_intent("Nisaidie kupata vifaa vya kujifunzia.", language)
        self.assertIsNotNone(match)
        self.assertEqual(match.entry.intent, "learning_materials")

    def test_prompt_pairs_map_to_their_service_without_verifying_translation(self):
        samples = [
            ("How can I see my marks?", "en", "grade_access"),
            ("Ninawezaje kuona matokeo yangu?", "sw", "grade_access"),
            ("Find course materials", "en", "learning_materials"),
            ("Nisaidie kupata vifaa vya kujifunzia.", "sw", "learning_materials"),
            ("Where can I find my assignment?", "en", "assignment_status"),
            ("Ninaipata wapi assignment yangu?", "sw", "assignment_status"),
        ]
        for query, language, intent in samples:
            with self.subTest(query=query):
                match = match_intent(query, language)
                self.assertIsNotNone(match)
                self.assertEqual(match.entry.intent, intent)

    def test_small_spelling_error_is_tolerated_against_a_source_label(self):
        match = match_intent("My coursse", "en")
        self.assertIsNotNone(match)
        self.assertEqual(match.entry.intent, "course_navigation")

    def test_ambiguous_query_requests_clarification(self):
        LexiconEntry.objects.create(
            canonical="portal update", language="en", intent="course_navigation",
            synonyms=["portal status"], provenance="Synthetic test fixture.",
            verification_status=LexiconEntry.Verification.SYNTHETIC,
        )
        LexiconEntry.objects.create(
            canonical="account update", language="en", intent="general_navigation_help",
            synonyms=["portal status"], provenance="Synthetic test fixture.",
            verification_status=LexiconEntry.Verification.SYNTHETIC,
        )
        match = match_intent("portal status", "en")
        self.assertIsNotNone(match)
        self.assertTrue(match.ambiguous)

    def test_role_restricted_entry_is_not_matched_for_students(self):
        LexiconEntry.objects.create(
            canonical="lecturer-only report", language="en", intent="private_report",
            synonyms=["lecturer report"], allowed_roles=["lecturer"],
            provenance="Synthetic test fixture.", verification_status=LexiconEntry.Verification.SYNTHETIC,
        )
        self.assertIsNone(match_intent("lecturer report", "en", role="student"))
