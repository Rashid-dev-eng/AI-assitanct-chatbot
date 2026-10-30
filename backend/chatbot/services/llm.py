"""Small provider boundary for grounded, OpenAI-compatible chat/embedding APIs."""
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ProviderUnavailable(Exception):
    pass


def _headers():
    return {"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"}


def embed_text(text: str) -> list[float]:
    if not settings.EMBEDDING_MODEL or not settings.LLM_API_KEY:
        return []
    response = requests.post(
        f"{settings.LLM_BASE_URL.rstrip('/')}/embeddings",
        headers=_headers(),
        json={"model": settings.EMBEDDING_MODEL, "input": text[:8000]},
        timeout=settings.LLM_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def chat_completion(messages: list[dict], tools: list[dict] | None = None) -> dict:
    if not settings.LLM_MODEL or not settings.LLM_API_KEY:
        raise ProviderUnavailable("LLM provider is not configured")
    try:
        response = requests.post(
            f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
            headers=_headers(),
            json={"model": settings.LLM_MODEL, "messages": messages, "temperature": 0.1, "max_tokens": settings.LLM_MAX_TOKENS, **({"tools": tools, "tool_choice": "auto"} if tools else {})},
            timeout=settings.LLM_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        message = payload["choices"][0]["message"]
        if not isinstance(message, dict):
            raise ProviderUnavailable("Malformed provider response")
        return message
    except requests.HTTPError as exc:
        response = exc.response
        status = response.status_code if response is not None else "unknown"
        details = ""
        if response is not None:
            try:
                error = response.json().get("error", {})
                if isinstance(error, dict):
                    code = error.get("code") or error.get("type") or ""
                    message = error.get("message") or ""
                    details = ", ".join(str(value) for value in (code, message) if value)
            except (ValueError, AttributeError):
                details = ""
        if settings.LLM_API_KEY:
            details = details.replace(settings.LLM_API_KEY, "[redacted]")
        logger.warning("OpenAI-compatible chat request returned HTTP %s (%s)", status, details[:300])
        raise ProviderUnavailable("LLM provider request failed") from exc
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning("Grounded LLM request failed (%s)", type(exc).__name__)
        raise ProviderUnavailable("LLM provider request failed") from exc
