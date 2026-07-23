from __future__ import annotations

import difflib
import re


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "what",
    "when",
    "which",
    "who",
    "why",
    "with",
}


def normalize_text(value: str | None, *, remove_stopwords: bool = False) -> str:
    text = str(value or "").lower()
    text = re.sub(r"\bquestion\s+\d+\b", " ", text)
    text = re.sub(r"\b\d+\b", " # ", text)
    text = re.sub(r"[^a-z0-9#\s]", " ", text)
    words = [word for word in text.split() if word]

    if remove_stopwords:
        words = [word for word in words if word not in STOPWORDS]

    return " ".join(words)


def token_set(value: str | None) -> set[str]:
    return set(normalize_text(value, remove_stopwords=True).split())


def jaccard_similarity(left: str | None, right: str | None) -> float:
    left_tokens = token_set(left)
    right_tokens = token_set(right)

    if not left_tokens or not right_tokens:
        return 0.0

    return len(left_tokens.intersection(right_tokens)) / len(left_tokens.union(right_tokens))


def string_similarity(left: str | None, right: str | None) -> float:
    return difflib.SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def likely_duplicate(left: str | None, right: str | None, *, threshold: float = 0.85) -> bool:
    if normalize_text(left, remove_stopwords=True) == normalize_text(right, remove_stopwords=True):
        return True

    token_overlap = jaccard_similarity(left, right)

    if token_overlap >= threshold:
        return True

    if token_overlap < 0.8:
        return False

    return string_similarity(left, right) >= threshold


def opening_pattern(value: str | None, word_count: int = 8) -> str:
    words = normalize_text(value, remove_stopwords=False).split()
    return " ".join(words[:word_count])
