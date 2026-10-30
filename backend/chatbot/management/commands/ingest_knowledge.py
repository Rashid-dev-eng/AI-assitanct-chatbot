import hashlib
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from chatbot.models import KnowledgeChunk, KnowledgeDocument
from chatbot.services.llm import embed_text

SUPPORTED = {".md", ".txt", ".html", ".htm", ".docx"}


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        with zipfile.ZipFile(path) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        return "\n".join("".join(node.itertext()) for node in root.findall(".//w:p", ns))
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".html", ".htm"}:
        text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&#160;", " ", text, flags=re.I)
    return re.sub(r"[ \t]+", " ", text).strip()


def make_chunks(text: str, max_chars: int = 1200):
    heading = ""
    current = []
    size = 0
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+)$", line.strip())
        if match:
            if current:
                yield heading, "\n".join(current).strip()
                current, size = [], 0
            heading = match.group(1).strip()
            continue
        for paragraph in re.split(r"\n\s*\n", line.strip()):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if current and size + len(paragraph) > max_chars:
                yield heading, "\n".join(current).strip()
                current, size = [], 0
            current.append(paragraph)
            size += len(paragraph)
    if current:
        yield heading, "\n".join(current).strip()


class Command(BaseCommand):
    help = "Ingest source files into review-pending, provenance-tracked knowledge chunks."

    def add_arguments(self, parser):
        parser.add_argument("source_dir", type=Path)
        parser.add_argument("--report", type=Path, default=None)

    def handle(self, *args, **options):
        root = options["source_dir"].resolve()
        if not root.is_dir():
            raise CommandError(f"Source directory does not exist: {root}")
        report = {"sourceDirectory": str(root), "indexedFiles": [], "skippedFiles": [], "failures": [], "chunksCreated": 0, "chunksSkippedAsDuplicates": 0, "verificationStatus": "pending_review", "notes": ["Ingested material is not used in answers until a reviewer approves it.", "Images/PDF screenshots are not OCR-processed; provide extracted text or transcribe and review it."]}
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name.endswith(".metadata.json"):
                continue
            if path.suffix.lower() not in SUPPORTED:
                report["skippedFiles"].append({"file": str(path.relative_to(root)), "reason": "unsupported format"})
                continue
            try:
                text = extract_text(path)
                if not text.strip():
                    report["skippedFiles"].append({"file": str(path.relative_to(root)), "reason": "no extractable text"})
                    continue
                metadata_path = path.with_suffix(path.suffix + ".metadata.json")
                metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
                source = path.relative_to(root).as_posix()
                source_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                doc_id = metadata.get("document_id") or source
                title = metadata.get("title") or path.stem.replace("_", " ").replace("-", " ")
                doc, created = KnowledgeDocument.objects.get_or_create(
                    content_hash=source_hash,
                    defaults={
                        "document_id": doc_id, "title": title, "body": text, "language": metadata.get("language", "en"),
                        "source_url": metadata.get("source_url", ""), "provenance": metadata.get("provenance", f"Ingested from supplied source file {source}; requires review."),
                        "source_file": source, "document_version": str(metadata.get("document_version", "1")),
                        "canonical_topic": metadata.get("canonical_topic", ""), "source_type": path.suffix.lstrip("."),
                        "allowed_roles": metadata.get("allowed_roles", []), "verification_status": KnowledgeDocument.Verification.PENDING,
                    },
                )
                if not created and doc.source_file and doc.source_file != source:
                    report["skippedFiles"].append({"file": source, "reason": "duplicate document content", "duplicateOf": doc.source_file})
                    continue
                if not created and doc.verification_status == KnowledgeDocument.Verification.REJECTED:
                    report["skippedFiles"].append({"file": source, "reason": "matching rejected source already exists"})
                    continue
                local_count = 0
                with transaction.atomic():
                    for ordinal, (section, body) in enumerate(make_chunks(text)):
                        chunk_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
                        if KnowledgeChunk.objects.filter(content_hash=chunk_hash).exclude(document=doc).exists():
                            report["chunksSkippedAsDuplicates"] += 1
                            continue
                        vector = []
                        try:
                            vector = embed_text(body)
                        except Exception:
                            pass
                        KnowledgeChunk.objects.get_or_create(document=doc, ordinal=ordinal, defaults={
                            "title": f"{title} — {section}" if section else title, "body": body,
                            "source_section": section, "canonical_topic": metadata.get("canonical_topic", ""),
                            "interface_role": metadata.get("interface_role", ""), "language": metadata.get("language", "en"),
                            "source_type": path.suffix.lstrip("."), "document_version": str(metadata.get("document_version", "1")),
                            "content_hash": chunk_hash, "embedding": vector,
                        })
                        local_count += 1
                report["chunksCreated"] += local_count
                report["indexedFiles"].append({"file": source, "title": title, "documentId": str(doc.pk), "chunks": local_count, "status": "created" if created else "already_present_pending_review"})
            except Exception as exc:
                report["failures"].append({"file": str(path.relative_to(root)), "error": type(exc).__name__})
        report["generatedAt"] = timezone.now().isoformat()
        report_path = options["report"] or root / "ingestion-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Ingestion report: {report_path} | {len(report['indexedFiles'])} files, {report['chunksCreated']} chunks, {len(report['failures'])} failures"))
