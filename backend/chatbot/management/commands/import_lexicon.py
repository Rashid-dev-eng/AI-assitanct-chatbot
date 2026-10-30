import csv
import json
from datetime import datetime, time
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from chatbot.models import LexiconEntry, LexiconRevision
from chatbot.services.normalization import normalize_text

LIST_FIELDS = {
    "synonyms", "english_synonyms", "swahili_synonyms", "mixed_expressions",
    "spelling_variants", "abbreviations", "abbreviation_variants", "related_terms", "example_queries", "allowed_roles",
}
ALLOWED_FIELDS = {
    "canonical", "language", "intent", "domain", "service_area", "page_label", "navigation_path", "context_notes",
    "swahili_equivalent", "synonyms", "english_synonyms", "swahili_synonyms", "mixed_expressions", "spelling_variants",
    "abbreviations", "abbreviation_variants", "related_terms", "example_queries", "allowed_roles", "response_text",
    "source_reference", "provenance", "verification_status", "translation_status", "translation_source", "reviewer",
    "reviewed_at", "lexicon_version", "confidence_threshold", "needs_clarification_below", "is_active",
}
REQUIRED_FIELDS = {"canonical", "intent", "service_area", "source_reference", "provenance"}
MODEL_FIELDS = ALLOWED_FIELDS - {"reviewed_at"}


def read_dataset(path: Path) -> tuple[str, list[dict]]:
    if path.suffix.casefold() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return "1.0", [dict(row) for row in reader]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CommandError(f"Cannot read JSON dataset: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
        raise CommandError("JSON must be an object containing an entries array.")
        if not payload["entries"]:
            raise CommandError("Lexicon dataset has no entries.")
    return str(payload.get("version", "1.0")), payload["entries"]


class Command(BaseCommand):
    help = "Validate and import a provenance-backed CSV or JSON bilingual lexicon dataset."

    def add_arguments(self, parser):
        parser.add_argument("path", type=Path)
        parser.add_argument("--update-existing", action="store_true", help="Update matching canonical-term/intent entries and record a revision.")
        parser.add_argument("--change-note", default="Imported lexicon dataset")
        parser.add_argument("--changed-by", default="", help="Optional username recorded in the revision history.")

    def handle(self, *args, **options):
        path: Path = options["path"]
        if not path.is_file():
            raise CommandError(f"Dataset file not found: {path}")
        dataset_version, rows = read_dataset(path)
        if not rows:
            raise CommandError("Lexicon dataset has no entries.")
        errors = []
        seen = set()
        prepared = []
        for index, raw in enumerate(rows, start=1):
            if not isinstance(raw, dict):
                errors.append(f"entry {index}: expected an object")
                continue
            unknown = set(raw) - ALLOWED_FIELDS
            missing = {name for name in REQUIRED_FIELDS if not str(raw.get(name, "")).strip()}
            non_text_required = {name for name in REQUIRED_FIELDS if name in raw and not isinstance(raw[name], str)}
            if non_text_required:
                errors.append(f"entry {index}: required text fields must be strings: {sorted(non_text_required)}")
            if unknown:
                errors.append(f"entry {index}: unknown fields {sorted(unknown)}")
            if missing:
                errors.append(f"entry {index}: missing required fields {sorted(missing)}")
                continue
            row = {key: value for key, value in raw.items() if key in ALLOWED_FIELDS}
            row.setdefault("language", "en")
            row.setdefault("verification_status", LexiconEntry.Verification.PENDING)
            row.setdefault("translation_status", LexiconEntry.TranslationStatus.MISSING)
            row.setdefault("lexicon_version", dataset_version)
            for field in LIST_FIELDS:
                if field in row and isinstance(row[field], str):
                    try:
                        row[field] = json.loads(row[field])
                    except json.JSONDecodeError:
                        errors.append(f"entry {index}: {field} must be a JSON array in CSV input")
                        row[field] = []
                if field in row and (not isinstance(row[field], list) or any(not isinstance(value, str) for value in row[field])):
                    errors.append(f"entry {index}: {field} must be an array of strings")
            for flag in ("is_active",):
                if flag in row and isinstance(row[flag], str):
                    row[flag] = row[flag].strip().casefold() in {"1", "true", "yes", "on"}
            try:
                if "confidence_threshold" in row:
                    row["confidence_threshold"] = float(row["confidence_threshold"])
                if "needs_clarification_below" in row:
                    row["needs_clarification_below"] = float(row["needs_clarification_below"])
            except (ValueError, TypeError):
                errors.append(f"entry {index}: confidence thresholds must be numeric")
            status = row.get("translation_status")
            if status not in LexiconEntry.TranslationStatus.values:
                errors.append(f"entry {index}: invalid translation_status {status!r}")
            elif status == LexiconEntry.TranslationStatus.VERIFIED and not all([
                row.get("swahili_equivalent"), row.get("translation_source"), row.get("reviewer"), row.get("reviewed_at")
            ]):
                errors.append(f"entry {index}: verified translations require a Kiswahili equivalent, translation_source, reviewer and reviewed_at")
            verification = row.get("verification_status")
            if verification not in LexiconEntry.Verification.values:
                errors.append(f"entry {index}: invalid verification_status {verification!r}")
            elif verification == LexiconEntry.Verification.VERIFIED and not all([
                row.get("reviewed_at"), row.get("reviewer"), row.get("source_reference")
            ]):
                errors.append(f"entry {index}: verified institutional terms require reviewer, reviewed_at and source_reference")
            key = (normalize_text(str(row.get("canonical", ""))), normalize_text(str(row.get("intent", ""))), row.get("language"))
            if key in seen:
                errors.append(f"entry {index}: duplicate canonical/intent/language in this file")
            seen.add(key)
            try:
                row["_reviewed_at"] = self._parse_date(row.get("reviewed_at"))
            except ValueError as exc:
                errors.append(f"entry {index}: {exc}")
            fields_for_model = {key: value for key, value in row.items() if key in MODEL_FIELDS}
            fields_for_model["reviewed_at"] = row.get("_reviewed_at")
            try:
                LexiconEntry(**fields_for_model).full_clean(validate_unique=False, validate_constraints=False)
            except ValidationError as exc:
                errors.append(f"entry {index}: model validation failed: {exc.message_dict if hasattr(exc, 'message_dict') else exc.messages}")
            prepared.append(row)

        if errors:
            raise CommandError("Lexicon import rejected; no rows were written:\n- " + "\n- ".join(errors))

        actor = None
        if options["changed_by"]:
            actor = get_user_model().objects.filter(username=options["changed_by"]).first()
            if actor is None:
                raise CommandError(f"No user named {options['changed_by']!r} exists; no rows were written.")

        created = updated = 0
        with transaction.atomic():
            for row in prepared:
                defaults = {key: value for key, value in row.items() if key in MODEL_FIELDS}
                defaults["reviewed_at"] = row.get("_reviewed_at")
                existing = next((candidate for candidate in LexiconEntry.objects.filter(intent=row["intent"], language=row["language"])
                                 if normalize_text(candidate.canonical) == normalize_text(row["canonical"])), None)
                if existing and not options["update_existing"]:
                    raise CommandError(f"Duplicate database term {row['canonical']!r}/{row['intent']}; use --update-existing to record an update.")
                if existing:
                    latest_version = existing.revisions.order_by("-version").values_list("version", flat=True).first() or 0
                    next_version = latest_version + 1
                    for key, value in defaults.items():
                        setattr(existing, key, value)
                    existing.save()
                    entry = existing
                    updated += 1
                else:
                    entry = LexiconEntry.objects.create(**defaults)
                    next_version = 1
                    created += 1
                LexiconRevision.objects.create(
                    entry=entry,
                    version=next_version,
                    snapshot=self._snapshot(entry),
                    change_note=options["change_note"][:500],
                    changed_by=actor,
                )
        self.stdout.write(self.style.SUCCESS(f"Imported {created} new and {updated} updated lexicon entries from version {dataset_version}."))

    @staticmethod
    def _parse_date(value):
        if not value:
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(str(value))
            except ValueError:
                try:
                    parsed = datetime.combine(datetime.strptime(str(value), "%Y-%m-%d").date(), time.min)
                except ValueError as exc:
                    raise ValueError("reviewed_at must be ISO 8601") from exc
        return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed

    @staticmethod
    def _snapshot(entry):
        fields = ALLOWED_FIELDS - {"reviewed_at"}
        snapshot = {field: getattr(entry, field) for field in fields}
        snapshot["reviewed_at"] = entry.reviewed_at.isoformat() if entry.reviewed_at else None
        return snapshot
