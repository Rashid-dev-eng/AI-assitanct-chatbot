import re
import unicodedata

TOKEN_RE = re.compile(r"[\w']+", flags=re.UNICODE)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = "".join(char for char in unicodedata.normalize("NFD", value) if not unicodedata.combining(char))
    value = re.sub(r"[^\w\s']", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def tokens(value: str) -> list[str]:
    return TOKEN_RE.findall(normalize_text(value))
