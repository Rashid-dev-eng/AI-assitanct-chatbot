import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from chatbot.models import EvaluationCase, LexiconEntry

USER_EXAMPLES = [
    ("How can I see my marks?", "Ninawezaje kuona matokeo yangu?", "grade_access", "grades"),
    ("Find course materials", "Nisaidie kupata vifaa vya kujifunzia.", "learning_materials", "learning_materials"),
    ("Where can I find my assignment?", "Ninaipata wapi assignment yangu?", "assignment_status", "assignments"),
]


class Command(BaseCommand):
    help = "Load the source-traceable prototype lexicon and clearly labelled evaluation cases."

    def handle(self, *args, **options):
        source = Path(settings.BASE_DIR) / "data" / "lexicon_initial.json"
        try:
            dataset = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Initial lexicon dataset could not be read: {exc}") from exc
        rows = dataset.get("entries")
        if not isinstance(rows, list):
            raise CommandError("Initial lexicon dataset must contain an entries array.")

        # Retire the earlier fabricated synthetic seed set; preserve any reviewed or imported records.
        LexiconEntry.objects.filter(
            provenance="Synthetic example authored for local backend development; not DMI policy."
        ).update(is_active=False)
        EvaluationCase.objects.filter(dataset_label="synthetic-demo-v1").update(is_active=False)

        for item in rows:
            entry = dict(item)
            entry.setdefault("language", "en")
            entry.setdefault("domain", entry.get("service_area", ""))
            entry.setdefault("page_label", entry["canonical"])
            entry.setdefault("context_notes", "Exact label in checked-in prototype source; live-site presence and official meaning are unverified.")
            entry.setdefault("response_text", "")
            entry.setdefault("verification_status", LexiconEntry.Verification.PENDING)
            entry.setdefault("translation_status", LexiconEntry.TranslationStatus.MISSING)
            entry.setdefault("translation_source", "")
            entry.setdefault("reviewer", "")
            entry.setdefault("reviewed_at", None)
            entry.setdefault("lexicon_version", dataset.get("version", "1.0"))
            entry.setdefault("is_active", True)
            for field in ("synonyms", "english_synonyms", "swahili_synonyms", "mixed_expressions", "spelling_variants",
                          "abbreviations", "abbreviation_variants", "related_terms", "example_queries", "allowed_roles"):
                entry.setdefault(field, [])
            LexiconEntry.objects.update_or_create(
                canonical=entry.pop("canonical"),
                language=entry.pop("language"),
                intent=entry.pop("intent"),
                defaults=entry,
            )

        for english, swahili, intent, area in USER_EXAMPLES:
            for phrase, language in ((english, "en"), (swahili, "sw")):
                EvaluationCase.objects.update_or_create(
                    query=phrase,
                    language=language,
                    dataset_label="user-example-unverified-v1",
                    defaults={
                        "intended_intent": intent,
                        "expected_service_area": area,
                        "reference_answer": f"Correct handling: map this query to the {area} service intent, and do not invent a learner record or unreviewed official DMI navigation instruction.",
                        "reference_answer": f"Correct handling: map this query to the {area} service intent, and do not invent a learner record or unreviewed official DMI navigation instruction.",
                        "request_type": EvaluationCase.RequestType.SERVICE,
                        "translation_status": LexiconEntry.TranslationStatus.PROPOSED,
                        "source_reference": "User-provided example in development request; Kiswahili phrasing has not been independently validated.",
                        "is_synthetic": True,
                        "is_active": True,
                    },
                )

        EvaluationCase.objects.update_or_create(
            query="Translate Grades to Kiswahili",
            language="en",
            dataset_label="prototype-translation-v1",
            defaults={
                "intended_intent": "translation_lookup",
                "request_type": EvaluationCase.RequestType.TRANSLATION,
                "reference_answer": "Return no unverified translation; report translation status as missing/proposed.",
                "translation_status": LexiconEntry.TranslationStatus.MISSING,
                "source_reference": "Synthetic evaluator case; no official Kiswahili translation is available in checked-in sources.",
                "is_synthetic": True,
                "is_active": True,
            },
        )
        EvaluationCase.objects.update_or_create(
            query="What is my status?",
            language="en",
            dataset_label="prototype-clarification-v1",
            defaults={
                "intended_intent": "unknown",
                "request_type": EvaluationCase.RequestType.CLARIFICATION,
                "expects_clarification": True,
                "reference_answer": "Ask the user which DeLMS service or status they mean before answering.",
                "reference_answer": "Ask the user which DeLMS service or status they mean before answering.",
                "source_reference": "Synthetic evaluator case for the explicit clarification requirement.",
                "is_synthetic": True,
                "is_active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(rows)} source-referenced prototype terms, {len(USER_EXAMPLES) * 2} user-example service cases, "
            "and separate synthetic translation/clarification cases. Kiswahili entries remain unverified."
        ))
