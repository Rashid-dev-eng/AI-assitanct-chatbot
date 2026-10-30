"""Explicit least-privilege registry for model-requested backend tools."""
import json
from dataclasses import dataclass
from typing import Callable

from django.conf import settings

from chatbot.models import AuditEvent
from chatbot.services.knowledge import retrieve_knowledge
from integrations.moodle.adapter import MoodleAdapter


@dataclass(frozen=True)
class ToolContext:
    user: object
    principal_id: str
    trusted_role: str


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict
    handler: Callable
    permissions: tuple[str, ...]
    dependency: str
    timeout_seconds: int
    retries: int
    read_only: bool


def trusted_role(user) -> str:
    """Only server-authenticated attributes can grant role-specific retrieval."""
    role = getattr(user, "role", None)
    if role and role != "preview":
        return str(role)
    if getattr(user, "is_superuser", False):
        return "administrator"
    if getattr(user, "is_staff", False):
        return "staff"
    return "preview" if getattr(user, "username", "") == "demo-student" else "unknown"


def _search_knowledge(arguments: dict, context: ToolContext) -> dict:
    query = arguments.get("query")
    language = arguments.get("language", "en")
    if not isinstance(query, str) or not query.strip() or len(query) > 1000:
        raise ValueError("query must be a non-empty string of at most 1000 characters")
    if language not in {"en", "sw", "mixed"}:
        raise ValueError("language must be en, sw, or mixed")
    results = []
    for score, chunk in retrieve_knowledge(query.strip(), language, context.trusted_role, limit=4):
        results.append({
            "title": chunk.title,
            "excerpt": chunk.body[:2400],
            "sourceFile": chunk.document.source_file,
            "sourceSection": chunk.source_section,
            "sourceUrl": chunk.document.source_url or None,
            "verificationStatus": "verified",
            "relevance": round(score, 3),
        })
    return {"results": results, "retrievalStatus": "matched" if results else "no_match"}


def _integration_status(arguments: dict, context: ToolContext) -> dict:
    # This is a sanitized local configuration status check; it makes no external request.
    status = MoodleAdapter().status()
    return {
        "integration": "Moodle",
        "status": status["status"],
        "enabled": status["enabled"],
        "configured": status["configured"],
        "availableOperations": status["allowedOperations"],
        "liveDataAccess": False,
    }


REGISTRY = {
    "search_delms_knowledge": ToolSpec(
        name="search_delms_knowledge",
        description="Search reviewed, non-expired DeLMS help sources. Returns only public or server-role-authorized evidence. Use this before answering institutional navigation questions.",
        parameters={"type": "object", "properties": {
            "query": {"type": "string", "minLength": 1, "maxLength": 1000},
            "language": {"type": "string", "enum": ["en", "sw", "mixed"]},
        }, "required": ["query"], "additionalProperties": False},
        handler=_search_knowledge, permissions=("reviewed_public_knowledge",), dependency="reviewed local knowledge index",
        timeout_seconds=60, retries=0, read_only=True,
    ),
    "get_delms_integration_status": ToolSpec(
        name="get_delms_integration_status",
        description="Read the sanitized configured/disabled status of the Moodle adapter. This does not query Moodle or retrieve learner data.",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        handler=_integration_status, permissions=("authenticated_preview",), dependency="local Moodle adapter configuration",
        timeout_seconds=2, retries=0, read_only=True,
    ),
}


def available_tools(user) -> list[ToolSpec]:
    if not getattr(user, "is_authenticated", False):
        return []
    if settings.DEBUG and settings.DEMO_AUTH_MODE:
        # Only non-sensitive read-only tools are enabled in the unauthenticated preview.
        return [REGISTRY["search_delms_knowledge"], REGISTRY["get_delms_integration_status"]]
    # The deployed build still has no approved learner-data adapter. These two safe tools remain the entire surface.
    return [REGISTRY["search_delms_knowledge"], REGISTRY["get_delms_integration_status"]]


def openai_tool_definitions(user) -> list[dict]:
    return [{"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.parameters}} for tool in available_tools(user)]


def execute_tool(name: str, raw_arguments: str | dict, context: ToolContext) -> dict:
    tool = REGISTRY.get(name)
    if not tool or tool not in available_tools(context.user):
        _audit(context, name, "rejected")
        return {"ok": False, "error": "Requested tool is not available."}
    if "authenticated_preview" in tool.permissions and not getattr(context.user, "is_authenticated", False):
        _audit(context, name, "unauthorized")
        return {"ok": False, "error": "The current principal is not authorized for this tool."}
    try:
        arguments = raw_arguments if isinstance(raw_arguments, dict) else json.loads(raw_arguments)
        if not isinstance(arguments, dict):
            raise ValueError("Arguments must be a JSON object")
        allowed = set(tool.parameters["properties"])
        if set(arguments) - allowed:
            raise ValueError("Unexpected tool argument")
        result = tool.handler(arguments, context)
        _audit(context, name, "ok")
        return {"ok": True, "data": result}
    except (ValueError, TypeError, KeyError):
        _audit(context, name, "invalid_arguments")
        return {"ok": False, "error": "Tool arguments were invalid."}
    except Exception as exc:
        _audit(context, name, "failed")
        return {"ok": False, "error": "The requested service is unavailable."}


def _audit(context: ToolContext, name: str, outcome: str) -> None:
    # Never store model arguments, queries, tokens, or tool results in this audit record.
    try:
        AuditEvent.objects.create(actor_id=context.principal_id, event_type="agent.tool_executed", metadata={"tool": name[:80], "outcome": outcome})
    except Exception:
        # Tool success must not depend on an optional metadata audit write.
        pass
