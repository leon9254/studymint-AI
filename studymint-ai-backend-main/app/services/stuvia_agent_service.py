from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock, Thread
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.audit import AuditLog
from app.models.document import Document, DocumentStatus
from app.models.pdf_export import PdfExport, PdfExportStatus
from app.models.user import User, UserRole
from app.schemas.document import DocumentCreate
from app.schemas.stuvia_agent import StuviaAgentListing, StuviaAgentRunCreate, StuviaAgentTopic
from app.services.document_service import create_generated_document, get_document
from app.services.simple_pdf import render_study_document_pdf
from app.services.integration_service import (
    cached_stuvia_topics,
    clear_stuvia_topic_history,
    filter_unused_stuvia_topics,
    remember_stuvia_topic_pool,
    remember_stuvia_topics,
    stuvia_connection_settings,
    stuvia_topic_identity_keys,
)
from app.services.openai_client import OPENAI_API_KEY_MISSING_MESSAGE


STAGE_LABELS = {
    "queued": "Queued",
    "scraping_topics": "Topic scrape",
    "ranking_topics": "Topic ranking",
    "generating_documents": "Draft generation",
    "packaging_listings": "Listing package",
    "n8n_review": "Publishing handoff",
    "completed": "Complete",
    "failed": "Failed",
}

REJECTED_TOPIC_TEXT = {
    "login",
    "log in",
    "sign up",
    "signup",
    "register",
    "upload",
    "sell",
    "shopping cart",
    "terms",
    "privacy",
    "cookie",
    "cookies",
    "help",
    "contact",
    "home",
    "documents",
    "followers",
    "following",
    "reviews",
    "profile",
}

REJECTED_TOPIC_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bwidth\s*=",
        r"\binitial-scale\s*=",
        r"\bminimum-scale\s*=",
        r"\bmaximum-scale\s*=",
        r"\buser-scalable\s*=",
        r"\bdevice-width\b",
        r"\bviewport\b",
        r"\bcharset\b",
        r"\butf-?8\b",
        r"\bcontent-type\b",
        r"\btext/html\b",
        r"(?:©|\(c\)|copyright)",
        r"\bstuvia\s+international\s+bv\b",
        r"\bpowered\s+by\s+stuvia\b",
        r"\bmember\s+since\b",
        r"\blast\s+item\s+sold\b",
        r"\breviews?\s+received\b",
        r"\bpackage\s+deal\b",
        r"\bflashcards?\b",
        r"\bsend\s+message\b",
        r"\b(?:tiktok|instagram|facebook|twitter|x\.com|linkedin|youtube|snapchat|pinterest|reddit|discord|telegram|whatsapp)\b",
        r"^\s*(?:social\s+media\s+)?(?:profile\s+)?link\s*$",
        r"^\s*[a-z0-9_. -]{2,30}\s+link(?:\s+study\s+guide)?\s*$",
        r"\bfollow\s+(?:me|us|writer|author|seller)\b",
        r"\b(?:share|copy)\s+link\b",
        r"\bcitation\s+generator\b",
        r"\b(?:apa|mla|harvard|chicago)\s+citation\b",
        r"\bplagiarism\s+checker\b",
        r"\bgrammar\s+checker\b",
        r"\bai\s+(?:content\s+)?detector\b",
        r"\bsatisfaction\s+guarantee\b",
        r"\bmoney\s+back\b",
        r"\brefund(?:s|able)?\b",
        r"\bguarantee(?:d|s)?\b",
        r"\b(?:customer|buyer|seller)\s+(?:support|service|guarantee)\b",
        r"\bfrequently\s+asked\s+questions?\b",
        r"\bfaqs?\b",
        r"\bhelp\s+center\b",
        r"\bsupport\s+center\b",
        r"^\s*(?:true|false|null|undefined)\s*$",
        r"^\s*[\[{].*[\]}]\s*$",
        r"\.(?:css|js|mjs|map|png|jpe?g|svg|gif|webp|ico)(?:[?#]|$)",
        r"\b(?:https?:)?//",
    )
)

ACADEMIC_TOPIC_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:exam|test\s*bank|question(?:s)?|answer(?:s)?|study\s*guide|summary|notes|assignment|case\s*study|practice|quiz|midterm|final|assessment|objective\s+assessment|care\s+plan|rationale(?:s)?)\b",
        r"\b(?:nurs|nur|nr|hesi|ati|nclex|wgu|rn|pn|lpn|msn|bsn|pharm|pharmacology|pathophysiology|med(?:ical)?[- ]?surg(?:ical)?|anatomy|physiology|psych|biology|chemistry|business|accounting|economics|law|finance|networking|cybersecurity)\b",
        r"\b[A-Z]{2,}\s*[-/]?\s*\d{2,}[A-Z]?\b",
        r"\b\d{2,}\s+(?:actual|real|practice|questions?|answers?|rationales?)\b",
    )
)

RETRYABLE_GENERATION_ERROR_MARKERS = (
    "timed out",
    "request failed",
    "rate limit",
    "overloaded",
    "temporarily unavailable",
    "response ended with status",
    "response was not valid json",
    "response did not include output text",
    "response did not match",
    "did not appear grounded",
    "prohibited filler language",
    "returned 408",
    "returned 409",
    "returned 425",
    "returned 429",
    "returned 500",
    "returned 502",
    "returned 503",
    "returned 504",
)

PUBLISH_SUCCESS_STATUSES = {"published", "submitted_for_review", "dry_run_ready"}
PUBLISH_MARKETPLACE_READY_STATUSES = {"published"}


@dataclass
class StuviaAgentRun:
    run_id: str
    tenant_id: str
    user_id: str
    status: str
    stage: str
    stage_label: str
    message: str
    progress: int
    profile_url: str
    publish_mode: str
    topics: list[dict[str, Any]] = field(default_factory=list)
    listings: list[dict[str, Any]] = field(default_factory=list)
    n8n_status: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_runs: dict[str, StuviaAgentRun] = {}
_runs_lock = Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _public_run(run: StuviaAgentRun) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "status": run.status,
        "stage": run.stage,
        "stage_label": run.stage_label,
        "message": run.message,
        "progress": run.progress,
        "profile_url": run.profile_url,
        "publish_mode": run.publish_mode,
        "topics": run.topics,
        "listings": run.listings,
        "n8n_status": run.n8n_status,
        "error": run.error,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
    }


def _update_run(
    run_id: str,
    *,
    status: str | None = None,
    stage: str | None = None,
    message: str | None = None,
    progress: int | None = None,
    topics: list[dict[str, Any]] | None = None,
    listings: list[dict[str, Any]] | None = None,
    n8n_status: str | None = None,
    error: str | None = None,
) -> None:
    with _runs_lock:
        run = _runs.get(run_id)
        if not run:
            return
        if status is not None:
            run.status = status
        if stage is not None:
            run.stage = stage
            run.stage_label = STAGE_LABELS.get(stage, stage.replace("_", " ").title())
        if message is not None:
            run.message = message
        if progress is not None:
            run.progress = max(0, min(100, progress))
        if topics is not None:
            run.topics = topics
        if listings is not None:
            run.listings = listings
        if n8n_status is not None:
            run.n8n_status = n8n_status
        if error is not None:
            run.error = error
        run.updated_at = _now()


def _publish_listing_status(result: dict[str, Any]) -> str:
    result_status = str(result.get("status") or "").strip().lower()
    if result_status in PUBLISH_SUCCESS_STATUSES:
        return result_status
    return "publish_failed"


def _merge_publish_results_into_run(run_id: Any, results: list[dict[str, Any]]) -> None:
    run_key = str(run_id or "").strip()
    if not run_key:
        return

    result_by_document_id = {
        str(result.get("document_id") or "").strip(): result
        for result in results
        if isinstance(result, dict) and str(result.get("document_id") or "").strip()
    }
    if not result_by_document_id:
        return

    with _runs_lock:
        run = _runs.get(run_key)
        if not run:
            return

        updated_listings: list[dict[str, Any]] = []
        for listing in run.listings:
            document_id = str(listing.get("document_id") or "").strip()
            result = result_by_document_id.get(document_id)
            if not result:
                updated_listings.append(listing)
                continue

            updated_listing = dict(listing)
            updated_listing["status"] = _publish_listing_status(result)
            updated_listing["publish_status"] = str(result.get("status") or "").strip() or None
            updated_listing["stuvia_url"] = result.get("stuvia_url")
            updated_listing["error"] = str(result.get("error") or "").strip() or None
            updated_listings.append(updated_listing)

        failed_results = [
            result
            for result in result_by_document_id.values()
            if str(result.get("status") or "").strip().lower() not in PUBLISH_SUCCESS_STATUSES
        ]
        published_count = sum(
            1
            for result in result_by_document_id.values()
            if str(result.get("status") or "").strip().lower() == "published"
        )
        submitted_count = sum(
            1
            for result in result_by_document_id.values()
            if str(result.get("status") or "").strip().lower() == "submitted_for_review"
        )

        run.listings = updated_listings
        run.progress = 100
        if failed_results:
            first_error = str(failed_results[0].get("error") or "Stuvia publisher failed.").strip()
            run.status = "FAILED"
            run.stage = "failed"
            run.stage_label = STAGE_LABELS["failed"]
            run.message = f"Documents were generated, but Stuvia publishing failed: {first_error[:180]}"
            run.error = first_error
            run.n8n_status = f"publish_failed:{len(failed_results)}"
        else:
            run.status = "COMPLETED"
            run.stage = "completed"
            run.stage_label = STAGE_LABELS["completed"]
            run.error = None
            if published_count:
                run.message = f"Stuvia publish confirmed for {published_count} document(s)."
                run.n8n_status = f"published:{published_count}"
            elif submitted_count:
                run.message = f"Stuvia submission completed for {submitted_count} document(s). Visibility may require Stuvia review."
                run.n8n_status = f"submitted:{submitted_count}"
            else:
                run.message = "Stuvia publisher dry run completed."
                run.n8n_status = "dry_run_ready"
        run.updated_at = _now()


def _validate_stuvia_profile_url(profile_url: str) -> str:
    value = profile_url.strip()
    parsed = urllib.parse.urlparse(value)
    host = (parsed.hostname or "").lower()

    if parsed.scheme not in {"http", "https"} or not host:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter a valid Stuvia profile URL.")
    if host != "stuvia.com" and not host.endswith(".stuvia.com"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only stuvia.com profile URLs are supported.")

    return value


def _ensure_generation_configured() -> None:
    if not settings.OPENAI_API_KEY.strip():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=OPENAI_API_KEY_MISSING_MESSAGE)


def create_stuvia_agent_run(payload: StuviaAgentRunCreate, user: User) -> dict[str, Any]:
    profile_url = _validate_stuvia_profile_url(payload.profile_url)
    now = _now()
    run = StuviaAgentRun(
        run_id=str(uuid4()),
        tenant_id=user.tenant_id,
        user_id=user.id,
        status="QUEUED",
        stage="queued",
        stage_label=STAGE_LABELS["queued"],
        message="Agent run accepted by the backend.",
        progress=3,
        profile_url=profile_url,
        publish_mode=payload.publish_mode,
        created_at=now,
        updated_at=now,
    )
    with _runs_lock:
        _runs[run.run_id] = run
    return _public_run(run)


def get_stuvia_agent_run(run_id: str, user: User) -> dict[str, Any]:
    with _runs_lock:
        run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stuvia agent run not found")
    if user.role != UserRole.SUPER_ADMIN.value and (run.tenant_id != user.tenant_id or run.user_id != user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stuvia agent run not found")
    return _public_run(run)


def _fetch_url(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "StudyMintAI/0.1 (+https://studymint.local)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=settings.STUVIA_SCRAPE_TIMEOUT_SECONDS) as response:
        raw = response.read()
    return raw.decode("utf-8", "replace")


def _strip_tags(value: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<[^>]+>", " ", value)
    return html.unescape(value)


def _clean_topic_text(value: str) -> str:
    text = _strip_tags(value)
    text = re.sub(r"\s+", " ", text).strip(" \t\r\n-|:•")
    text = re.sub(r"\s+\|\s+Stuvia\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+-\s+Stuvia\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:USD|EUR|GBP)\s*\d+(?:[.,]\d{2})?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[$€£]\s*\d+(?:[.,]\d{2})?", "", text)
    return re.sub(r"\s+", " ", text).strip(" \t\r\n-|:•")


def _exact_scraped_title(value: Any) -> str:
    return _clean_topic_text(str(value or ""))[:255] or "Stuvia Study Document"


def _filename_stem_from_title(title: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", str(title or ""))
    stem = "-".join(word.lower() for word in words[:4])
    return stem or "stuvia-study-document"


def _document_pdf_filename(document: Document) -> str:
    return f"{_filename_stem_from_title(document.title)}-{str(document.id or uuid4())[:8]}.pdf"


def _normalize_stuvia_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse(parsed._replace(fragment=""))


def _has_academic_topic_signal(text: str) -> bool:
    cleaned = _clean_topic_text(text)
    if any(pattern.search(cleaned) for pattern in ACADEMIC_TOPIC_PATTERNS):
        return True
    words = re.findall(r"[A-Za-z0-9]+", cleaned)
    if len(words) >= 7 and re.search(r"\d", cleaned):
        return True
    return False


def _is_topic_candidate(value: str) -> bool:
    text = _clean_topic_text(value)
    lower = text.lower()

    if not (8 <= len(text) <= 180):
        return False
    if lower in REJECTED_TOPIC_TEXT:
        return False
    if any(pattern.search(text) for pattern in REJECTED_TOPIC_PATTERNS):
        return False
    if any(blocked in lower for blocked in ["javascript:", "enable cookies", "all rights reserved", "forgot password"]):
        return False
    if re.fullmatch(r"[\W_]+", text):
        return False
    if len(text.split()) < 2 and not re.search(r"[A-Z]{2,}\s*\d{2,}", text):
        return False
    if not _has_academic_topic_signal(text):
        return False
    return True


def _extract_links_from_html(page_html: str, base_url: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()

    for match in re.finditer(r"\bhref=[\"']([^\"'#]+)[\"']", page_html, flags=re.IGNORECASE):
        href = html.unescape(match.group(1)).strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:")):
            continue
        absolute = _normalize_stuvia_url(urllib.parse.urljoin(base_url, href))
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)

    return links


def _stuvia_profile_slug(profile_url: str) -> str:
    path = urllib.parse.urlparse(profile_url).path.strip("/")
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2 and parts[0].lower() == "user":
        return parts[1].lower()
    return parts[-1].lower() if parts else ""


def _is_stuvia_document_url(url: str) -> bool:
    path = urllib.parse.urlparse(url).path.lower()
    return any(
        marker in path
        for marker in (
            "/doc/",
            "/document/",
            "/documents/",
            "/bundle/",
            "/package/",
            "/summary/",
            "/exam/",
        )
    )


def _is_stuvia_profile_page_url(url: str, profile_url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    profile_slug = _stuvia_profile_slug(profile_url)
    path_parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(path_parts) < 2 or path_parts[0].lower() != "user" or path_parts[1].lower() != profile_slug:
        return False
    return len(path_parts) == 2


def _is_relevant_stuvia_link(url: str, profile_url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if host != "stuvia.com" and not host.endswith(".stuvia.com"):
        return False

    if _is_stuvia_profile_page_url(url, profile_url):
        return True
    return _is_stuvia_document_url(url)


def _seed_stuvia_page_urls(profile_url: str, page_limit: int) -> list[str]:
    urls = [_normalize_stuvia_url(profile_url)]
    parsed = urllib.parse.urlparse(profile_url)
    existing_query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    for page in range(2, min(page_limit, 8) + 1):
        query = dict(existing_query)
        query["page"] = str(page)
        urls.append(_normalize_stuvia_url(urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))))
    return urls


def _scrape_stuvia_topic_candidates(profile_url: str) -> list[str]:
    candidates: list[str] = []
    seen_urls: set[str] = set()
    queued_urls: list[str] = _seed_stuvia_page_urls(profile_url, settings.STUVIA_SCRAPE_PAGE_LIMIT)

    while queued_urls and len(seen_urls) < max(1, settings.STUVIA_SCRAPE_PAGE_LIMIT):
        url = queued_urls.pop(0)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        try:
            page_html = _fetch_url(url)
        except (urllib.error.URLError, TimeoutError, OSError):
            continue

        candidates.extend(_extract_topics_from_html(page_html, url))

        for link in _extract_links_from_html(page_html, url):
            if link in seen_urls or link in queued_urls:
                continue
            if _is_relevant_stuvia_link(link, profile_url):
                queued_urls.append(link)

    return candidates


def _walk_json_topics(value: Any) -> list[str]:
    topics: list[str] = []

    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"name", "headline", "title", "description", "keywords", "about"}:
                topics.extend(_walk_json_topics(item))
            elif isinstance(item, (dict, list)):
                topics.extend(_walk_json_topics(item))
    elif isinstance(value, list):
        for item in value:
            topics.extend(_walk_json_topics(item))
    elif isinstance(value, str):
        if "," in value and len(value) > 80:
            topics.extend(part.strip() for part in value.split(","))
        else:
            topics.append(value)

    return topics


def _html_attr(tag: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}=[\"']([^\"']*)[\"']", tag, flags=re.IGNORECASE)
    return html.unescape(match.group(1)).strip() if match else ""


def _extract_document_anchor_topics(page_html: str, base_url: str) -> list[str]:
    if not base_url:
        return []

    topics: list[str] = []
    for match in re.finditer(r"<a\b([^>]*)>(.*?)</a>", page_html, flags=re.IGNORECASE | re.DOTALL):
        attrs = match.group(1)
        href = _html_attr(attrs, "href")
        if not href:
            continue
        absolute = _normalize_stuvia_url(urllib.parse.urljoin(base_url, html.unescape(href).strip()))
        if not _is_stuvia_document_url(absolute):
            continue
        title = _html_attr(attrs, "title") or _html_attr(attrs, "aria-label") or match.group(2)
        cleaned = _clean_topic_text(title)
        if _is_topic_candidate(cleaned):
            topics.append(cleaned)

    return topics


def _extract_topics_from_html(page_html: str, base_url: str = "") -> list[str]:
    candidates: list[str] = []
    document_anchor_topics = _extract_document_anchor_topics(page_html, base_url)
    candidates.extend(document_anchor_topics)
    use_broad_page_signals = not base_url or _is_stuvia_document_url(base_url)

    if use_broad_page_signals:
        for match in re.finditer(
            r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
            page_html,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            try:
                payload = json.loads(html.unescape(match.group(1)).strip())
            except json.JSONDecodeError:
                continue
            candidates.extend(_walk_json_topics(payload))

        attribute_pattern = r"\b(?:title|aria-label)=[\"']([^\"']{8,240})[\"']"
        candidates.extend(match.group(1) for match in re.finditer(attribute_pattern, page_html, flags=re.IGNORECASE))

        allowed_meta_names = {
            "title",
            "og:title",
            "twitter:title",
            "description",
            "og:description",
            "twitter:description",
            "keywords",
        }
        for meta_match in re.finditer(r"<meta\b[^>]*>", page_html, flags=re.IGNORECASE):
            meta_tag = meta_match.group(0)
            name_match = re.search(r"\b(?:name|property|itemprop)=[\"']([^\"']+)[\"']", meta_tag, flags=re.IGNORECASE)
            if not name_match or name_match.group(1).strip().lower() not in allowed_meta_names:
                continue
            content_match = re.search(r"\bcontent=[\"']([^\"']{8,240})[\"']", meta_tag, flags=re.IGNORECASE)
            if content_match:
                candidates.append(content_match.group(1))

        tag_pattern = r"<(?:a|h1|h2|h3|h4|li|span|p|strong)[^>]*>(.{8,360}?)</(?:a|h1|h2|h3|h4|li|span|p|strong)>"
        candidates.extend(match.group(1) for match in re.finditer(tag_pattern, page_html, flags=re.IGNORECASE | re.DOTALL))

    cleaned: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        topic = _clean_topic_text(candidate)
        key = topic.lower()
        if key in seen or not _is_topic_candidate(topic):
            continue
        seen.add(key)
        cleaned.append(topic)

    return cleaned


def _valid_stuvia_topic_record(topic: dict[str, Any]) -> bool:
    title = _clean_topic_text(str(topic.get("title") or topic.get("topic") or ""))
    label = _clean_topic_text(str(topic.get("topic") or topic.get("title") or ""))
    if not _is_topic_candidate(title):
        return False
    return not any(pattern.search(label) for pattern in REJECTED_TOPIC_PATTERNS)


def _topic_label_from_title(title: str) -> str:
    label = _clean_topic_text(title)
    label = re.sub(r"\b(?:actual|complete|latest|verified|correct|answers?|questions?|question bank|test bank)\b", " ", label, flags=re.IGNORECASE)
    label = re.sub(r"\b(?:exam|final|midterm|study guide|summary|notes|bundle|pack)\b", " ", label, flags=re.IGNORECASE)
    label = re.sub(r"\b20\d{2}(?:[/.-]20\d{2})?\b", " ", label)
    label = re.sub(r"\b(?:100\s*%|graded\s*a\+?)\b", " ", label, flags=re.IGNORECASE)
    label = re.sub(r"[\(\)\[\]]", " ", label)
    label = re.sub(r"\s+", " ", label).strip(" -|:")
    return label[:120] or title[:120]


def _professional_title(topic_label: str, source_title: str) -> str:
    base = _clean_topic_text(source_title)
    if len(base) > 105 or re.search(r"\b(?:100\s*%|actual|verified|correct answers)\b", base, flags=re.IGNORECASE):
        base = f"{topic_label} Practice Question Bank"
    if "question" not in base.lower() and "exam" not in base.lower() and "guide" not in base.lower():
        base = f"{base} Study Guide"
    return base[:160]


def _rank_topics_heuristic(candidates: list[str], source_url: str, limit: int) -> list[dict[str, Any]]:
    counts = Counter(candidate.lower() for candidate in candidates)
    ranked: list[tuple[float, str]] = []

    for index, candidate in enumerate(candidates):
        lower = candidate.lower()
        score = counts[lower] * 8 - index * 0.05
        if re.search(r"\b(?:exam|test bank|question|nurs|hesi|ati|case|assignment|summary|notes|study guide)\b", lower):
            score += 10
        if re.search(r"\b[A-Z]{2,}\s*\d{2,}\b", candidate):
            score += 6
        if len(candidate.split()) >= 5:
            score += 3
        ranked.append((score, candidate))

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected: list[dict[str, Any]] = []
    seen_labels: set[str] = set()

    for score, candidate in ranked:
        topic = _topic_label_from_title(candidate)
        key = topic.lower()
        if key in seen_labels:
            continue
        seen_labels.add(key)
        scraped_title = _exact_scraped_title(candidate)
        selected.append(
            StuviaAgentTopic(
                title=scraped_title,
                topic=topic,
                source_url=source_url,
                score=round(score, 2),
                reason="Ranked from repeated profile title/topic signals; title preserved from scraped source.",
            ).model_dump()
        )
        if len(selected) >= limit:
            break

    return selected


def _rank_topics_with_langchain(candidates: list[str], source_url: str, limit: int) -> list[dict[str, Any]] | None:
    if not settings.OPENAI_API_KEY.strip():
        return None

    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI
        from langsmith import traceable
        from pydantic import BaseModel, Field
    except Exception:
        return None

    class TopicSelectionItem(BaseModel):
        candidate_index: int = Field(description="Zero-based index of the exact scraped candidate to use")
        topic: str = Field(description="Concise academic topic label")
        reason: str = Field(description="Short reason this topic was selected")

    class TopicSelection(BaseModel):
        topics: list[TopicSelectionItem] = Field(max_length=limit)

    @traceable(name="stuvia_topic_ranker")
    def invoke_ranker() -> TopicSelection:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Select marketplace topic signals for original study documents. "
                    "Return only indexes from the provided scraped strings. Do not rewrite the selected title.",
                ),
                (
                    "human",
                    "Return the top {limit} topics from these indexed scraped Stuvia profile strings as structured JSON:\n{candidates}",
                ),
            ]
        )
        llm = ChatOpenAI(model=settings.OPENAI_FAST_MODEL, temperature=0, timeout=settings.OPENAI_TIMEOUT_SECONDS)
        chain = prompt | llm.with_structured_output(TopicSelection)
        indexed_candidates = [
            {"index": index, "title": candidate}
            for index, candidate in enumerate(candidates[:80])
        ]
        return chain.invoke({"limit": limit, "candidates": json.dumps(indexed_candidates, ensure_ascii=False)})

    try:
        selection = invoke_ranker()
    except Exception:
        return None

    topics: list[dict[str, Any]] = []
    for index, item in enumerate(selection.topics[:limit]):
        if item.candidate_index < 0 or item.candidate_index >= min(len(candidates), 80):
            continue
        title = _exact_scraped_title(candidates[item.candidate_index])
        topic = _clean_topic_text(item.topic)
        if not topic:
            topic = _topic_label_from_title(title)
        if not title or not topic:
            continue
        topics.append(
            StuviaAgentTopic(
                title=title,
                topic=topic[:120],
                source_url=source_url,
                score=100 - index,
                reason=(item.reason[:220] or "Selected by LLM ranker; title preserved from scraped source."),
            ).model_dump()
        )

    return topics or None


def discover_stuvia_topics(profile_url: str, manual_topics: list[str], limit: int) -> list[dict[str, Any]]:
    candidates = [_clean_topic_text(topic) for topic in manual_topics if _is_topic_candidate(topic)]
    candidates.extend(_scrape_stuvia_topic_candidates(profile_url))

    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No usable Stuvia topics were found. Add manual topics or try again when the profile is reachable.",
        )

    if settings.STUVIA_AGENT_USE_LLM_RANKER:
        langchain_topics = _rank_topics_with_langchain(candidates, profile_url, limit)
        if langchain_topics:
            valid_langchain_topics = [topic for topic in langchain_topics if _valid_stuvia_topic_record(topic)]
            if valid_langchain_topics:
                return valid_langchain_topics[:limit]

    return [topic for topic in _rank_topics_heuristic(candidates, profile_url, limit) if _valid_stuvia_topic_record(topic)][:limit]


def _topics_from_cache_or_scrape(run_id: str, tenant_id: str, profile_url: str, payload: StuviaAgentRunCreate) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        if payload.reset_topic_history:
            clear_stuvia_topic_history(db, tenant_id)
        cached_topics = cached_stuvia_topics(db, tenant_id, profile_url, payload.max_topics)
    cached_topics = [topic for topic in cached_topics if _valid_stuvia_topic_record(topic)]

    if len(cached_topics) >= payload.max_topics:
        _update_run(
            run_id,
            stage="ranking_topics",
            topics=cached_topics,
            message=f"Selected {len(cached_topics)} unused topic(s) from the cached Stuvia topic pool.",
            progress=34,
        )
        return cached_topics

    needed = payload.max_topics - len(cached_topics)
    _update_run(
        run_id,
        status="RUNNING",
        stage="scraping_topics",
        message=f"Cached Stuvia topic pool has {len(cached_topics)} unused topic(s); scraping for at least {needed} more.",
        progress=14,
        topics=cached_topics,
    )
    discovery_limit = max(payload.max_topics * 20, 150)
    discovered_topics = discover_stuvia_topics(profile_url, payload.manual_topics, discovery_limit)
    discovered_topics = [topic for topic in discovered_topics if _valid_stuvia_topic_record(topic)]

    with SessionLocal() as db:
        remember_stuvia_topic_pool(db, tenant_id, profile_url, discovered_topics)
        topics = cached_stuvia_topics(db, tenant_id, profile_url, payload.max_topics)
        topics = [topic for topic in topics if _valid_stuvia_topic_record(topic)]
        if len(topics) < payload.max_topics:
            supplemental = filter_unused_stuvia_topics(db, tenant_id, discovered_topics, payload.max_topics)
            topic_ids = {tuple(sorted(stuvia_topic_identity_keys(topic))) for topic in topics}
            for topic in supplemental:
                if not _valid_stuvia_topic_record(topic):
                    continue
                topic_id = tuple(sorted(stuvia_topic_identity_keys(topic)))
                if topic_id in topic_ids:
                    continue
                topics.append(topic)
                topic_ids.add(topic_id)
                if len(topics) >= payload.max_topics:
                    break

    if not topics:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No unused Stuvia topics are available for this tenant. "
                "The cached pool was exhausted and the latest scrape did not find new usable topics."
            ),
        )

    _update_run(
        run_id,
        stage="ranking_topics",
        topics=topics,
        message=f"Selected {len(topics)} unused topic(s); refreshed the cached pool with {len(discovered_topics)} scraped topic signals.",
        progress=34,
    )
    return topics[: payload.max_topics]


def _listing_url(document_id: str) -> str:
    base = settings.FRONTEND_PUBLIC_URL.rstrip("/")
    return f"{base}/documents/{document_id}/studio"


def _stuvia_document_title(base_title: str, document_id: str) -> str:
    return _exact_scraped_title(base_title)


def _rename_stuvia_document_for_listing(document: Any, topic: dict[str, Any]) -> str:
    final_title = _stuvia_document_title(str(topic.get("title") or document.title), document.id)
    document.title = final_title

    latest = max(document.versions, key=lambda version: version.version_number, default=None)
    if latest:
        content = dict(latest.content or {})
        content["title_page"] = final_title
        metadata = dict(content.get("metadata") or {})
        metadata["stuvia_source_title"] = final_title
        metadata["stuvia_listing_title"] = final_title
        metadata["stuvia_pdf_filename"] = _document_pdf_filename(document)
        content["metadata"] = metadata
        latest.content = content

    return final_title


def _document_payload_for_topic(topic: dict[str, Any], payload: StuviaAgentRunCreate) -> DocumentCreate:
    question_count = payload.question_count if payload.document_type == "Question Bank" else None
    source_notes = payload.source_notes if payload.generation_mode == "SOURCE_GROUNDED" else ""
    instructions = "\n".join(
        part
        for part in [
            payload.user_instructions.strip(),
            "Use this scraped topic only as a demand signal. Create original study content and avoid copying seller text, claims, prices, or platform wording.",
            f"Topic signal: {topic['topic']}",
        ]
        if part
    )

    return DocumentCreate(
        title=topic["title"],
        subject=topic["topic"][:255],
        education_level=payload.education_level,
        document_type=payload.document_type,
        target_platform="Stuvia",
        output_language=payload.output_language,
        length=payload.length,
        template_id=payload.template_id or None,
        question_count=question_count,
        generation_mode=payload.generation_mode,
        user_instructions=instructions[:4000],
        source_notes=source_notes,
        difficulty=payload.difficulty,
        speed_mode=True,
    )


def _generate_listing_for_topic(
    run_id: str,
    payload: StuviaAgentRunCreate,
    user_id: str,
    topic: dict[str, Any],
    index: int,
    total: int,
    attempt: int = 1,
) -> dict[str, Any]:
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user:
            raise RuntimeError("Requesting user no longer exists")

        def progress_callback(stage: str, message: str, progress: int) -> None:
            aggregate = 38 + int(((index + (progress / 100)) / max(total, 1)) * 42)
            retry_label = "" if attempt == 1 else f" retry {attempt}"
            _update_run(
                run_id,
                status="RUNNING",
                stage="generating_documents",
                message=f"{topic['title']}{retry_label}: {message}",
                progress=aggregate,
            )

        document = create_generated_document(db, _document_payload_for_topic(topic, payload), user, progress_callback=progress_callback)
        final_title = _rename_stuvia_document_for_listing(document, topic)
        db.commit()

    return StuviaAgentListing(
        title=final_title,
        topic=topic["topic"],
        document_id=document.id,
        document_url=_listing_url(document.id),
        status="ready_for_review",
        attempts=attempt,
    ).model_dump()


def _generation_error_message(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        return str(exc.detail)
    return str(exc)


def _is_retryable_generation_error(exc: Exception) -> bool:
    if isinstance(exc, HTTPException) and exc.status_code in {
        status.HTTP_408_REQUEST_TIMEOUT,
        status.HTTP_409_CONFLICT,
        status.HTTP_425_TOO_EARLY,
        status.HTTP_429_TOO_MANY_REQUESTS,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        status.HTTP_502_BAD_GATEWAY,
        status.HTTP_503_SERVICE_UNAVAILABLE,
        status.HTTP_504_GATEWAY_TIMEOUT,
    }:
        return True

    message = _generation_error_message(exc).lower()
    return any(marker in message for marker in RETRYABLE_GENERATION_ERROR_MARKERS)


def _failed_listing_for_topic(topic: dict[str, Any], exc: Exception, attempt: int, will_retry: bool) -> dict[str, Any]:
    message = _generation_error_message(exc)
    return StuviaAgentListing(
        title=topic["title"],
        topic=topic["topic"],
        status="retrying" if will_retry else "failed",
        error=message,
        attempts=attempt,
    ).model_dump()


def _ordered_listings(results: dict[int, dict[str, Any]], total: int) -> list[dict[str, Any]]:
    return [results[index] for index in range(total) if index in results]


def _generate_documents(run_id: str, payload: StuviaAgentRunCreate, user_id: str, topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    max_workers = max(1, min(payload.concurrency, settings.STUVIA_AGENT_MAX_CONCURRENCY, len(topics)))
    max_attempts = max(1, settings.STUVIA_AGENT_GENERATION_ATTEMPTS)
    recovery_workers = max(1, min(settings.STUVIA_AGENT_RECOVERY_CONCURRENCY, max_workers))
    results: dict[int, dict[str, Any]] = {}
    pending_indexes = list(range(len(topics)))

    for attempt in range(1, max_attempts + 1):
        workers = max_workers if attempt == 1 else min(recovery_workers, len(pending_indexes))
        if attempt > 1:
            delay = settings.STUVIA_AGENT_RETRY_BACKOFF_SECONDS * (attempt - 1)
            if delay > 0:
                time.sleep(delay)
            _update_run(
                run_id,
                status="RUNNING",
                stage="generating_documents",
                message=f"Retrying {len(pending_indexes)} timed-out or rate-limited draft(s) with controlled concurrency.",
                progress=min(84, 68 + attempt * 4),
                listings=_ordered_listings(results, len(topics)),
            )

        next_pending: list[int] = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _generate_listing_for_topic,
                    run_id,
                    payload,
                    user_id,
                    topics[index],
                    index,
                    len(topics),
                    attempt,
                ): index
                for index in pending_indexes
            }
            for future in as_completed(futures):
                index = futures[future]
                topic = topics[index]
                try:
                    listing = future.result()
                except (HTTPException, SQLAlchemyError, RuntimeError, ValueError) as exc:
                    will_retry = attempt < max_attempts and _is_retryable_generation_error(exc)
                    listing = _failed_listing_for_topic(topic, exc, attempt, will_retry)
                    if will_retry:
                        next_pending.append(index)

                results[index] = listing
                _update_run(run_id, listings=_ordered_listings(results, len(topics)))

        pending_indexes = sorted(next_pending)
        if not pending_indexes:
            break

    listings = _ordered_listings(results, len(topics))
    listings.sort(key=lambda item: item["title"])
    return listings


def _topics_for_successful_listings(topics: list[dict[str, Any]], listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    successful_keys: set[str] = set()
    for listing in listings:
        if listing.get("status") == "failed":
            continue
        successful_keys.update(stuvia_topic_identity_keys(listing))

    return [topic for topic in topics if stuvia_topic_identity_keys(topic) & successful_keys]


def _valid_n8n_webhook_url(webhook_url: str) -> bool:
    parsed = urllib.parse.urlparse(webhook_url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _credential_lookup_url(tenant_id: str) -> str:
    return f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}{settings.API_V1_PREFIX}/integrations/stuvia/internal-credentials/{tenant_id}"


def _configured_browser_publisher_url(connection: dict[str, Any]) -> str:
    configured_url = settings.STUVIA_BROWSER_PUBLISHER_URL.strip()
    if configured_url:
        return configured_url

    url = str(connection.get("browser_publisher_url") or "").strip()
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname == "backend" and parsed.path.endswith("/api/v1/stuvia-agent/publisher/handoff"):
        return ""
    if parsed.hostname in {"localhost", "127.0.0.1"}:
        return ""
    return url


def _deliver_n8n_payload(webhook_url: str, webhook_token: str, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "StudyMintAI/0.1"}
    if webhook_token:
        headers["Authorization"] = f"Bearer {webhook_token}"

    request = urllib.request.Request(webhook_url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=settings.N8N_STUVIA_WEBHOOK_TIMEOUT_SECONDS) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        print(f"n8n webhook delivery returned HTTP {exc.code}: {detail}", flush=True)
    except Exception as exc:
        print(f"n8n webhook delivery failed after queue handoff: {exc}", flush=True)


def _send_n8n_payload(webhook_url: str, webhook_token: str, payload: dict[str, Any]) -> str:
    try:
        Thread(target=_deliver_n8n_payload, args=(webhook_url, webhook_token, payload), daemon=True).start()
    except Exception as exc:
        return f"failed:{exc}"
    return "sent:queued"


def _publisher_auth_token(connection: dict[str, Any]) -> str:
    return settings.N8N_STUVIA_WEBHOOK_TOKEN.strip() or str(connection.get("n8n_webhook_token") or "").strip()


def _send_browser_publisher_payload(publisher_url: str, publisher_token: str, payload: dict[str, Any]) -> str:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "StudyMintAI/0.1"}
    if publisher_token:
        headers["Authorization"] = f"Bearer {publisher_token}"

    request = urllib.request.Request(publisher_url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=min(settings.N8N_STUVIA_WEBHOOK_TIMEOUT_SECONDS, 15)) as response:
            raw = response.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {}
        status_value = str(parsed.get("status") or "").strip().lower()
        if status_value == "queued" or parsed.get("ok") is True:
            return "publisher:queued"
        return f"failed:publisher returned {status_value or 'unknown'}"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        return f"failed:publisher HTTP {exc.code}: {detail}"
    except Exception as exc:
        return f"failed:publisher {exc}"


def _n8n_payload(
    *,
    run_id: str,
    tenant_id: str,
    profile_url: str,
    publish_mode: str,
    auto_publish_requested: bool,
    manual_publish_requested: bool,
    connection: dict[str, Any],
    topics: list[dict[str, Any]],
    listings: list[dict[str, Any]],
) -> dict[str, Any]:
    review_required = not auto_publish_requested and not manual_publish_requested
    return {
        "run_id": run_id,
        "tenant_id": tenant_id,
        "profile_url": profile_url,
        "publish_mode": publish_mode,
        "auto_publish_requested": auto_publish_requested,
        "manual_publish_requested": manual_publish_requested,
        "credential_storage": "backend_encrypted",
        "credential_lookup_url": _credential_lookup_url(tenant_id),
        "stuvia_credential_name": str(connection.get("stuvia_credential_name") or "Stuvia Account"),
        "browser_publisher_url": _configured_browser_publisher_url(connection),
        "topics": topics,
        "listings": listings,
        "review_required": review_required,
        "posting_policy": (
            "Manual publish requested from StudyMint. The private publisher must fetch stored Stuvia credentials through the internal lookup endpoint."
            if manual_publish_requested
            else "Auto-publish requested. The private publisher must fetch stored Stuvia credentials through the internal lookup endpoint."
            if auto_publish_requested
            else "Drafts are prepared for human review or authorized API posting only."
        ),
    }


def _send_to_n8n(run_id: str, payload: StuviaAgentRunCreate, topics: list[dict[str, Any]], listings: list[dict[str, Any]], tenant_id: str) -> str:
    if payload.publish_mode == "drafts_only":
        return "drafts_only"

    with SessionLocal() as db:
        connection = stuvia_connection_settings(db, tenant_id)

    webhook_url = str(connection.get("n8n_webhook_url") or "").strip()

    if payload.publish_mode == "n8n_auto_publish" and not bool(connection.get("auto_publish_enabled")):
        return "auto_publish_disabled"

    auto_publish_requested = payload.publish_mode == "n8n_auto_publish" and bool(connection.get("auto_publish_enabled"))
    n8n_payload = _n8n_payload(
        run_id=run_id,
        tenant_id=tenant_id,
        profile_url=payload.profile_url,
        publish_mode=payload.publish_mode,
        auto_publish_requested=auto_publish_requested,
        manual_publish_requested=False,
        connection=connection,
        topics=topics,
        listings=listings,
    )
    webhook_token = str(connection.get("n8n_webhook_token") or "").strip()
    publisher_url = str(n8n_payload.get("browser_publisher_url") or "").strip()
    if auto_publish_requested and publisher_url:
        return _send_browser_publisher_payload(publisher_url, _publisher_auth_token(connection), n8n_payload)
    if not webhook_url:
        return "not_configured"
    if not _valid_n8n_webhook_url(webhook_url):
        return "invalid_webhook_url"
    return _send_n8n_payload(webhook_url, webhook_token, n8n_payload)


def _manual_publish_topic(document: Document) -> dict[str, Any]:
    return StuviaAgentTopic(
        title=document.title,
        topic=document.subject,
        source_url="manual_publish",
        score=100,
        reason="Manual publish requested from the document studio.",
    ).model_dump()


def _manual_publish_listing(document: Document) -> dict[str, Any]:
    return StuviaAgentListing(
        title=document.title,
        topic=document.subject,
        document_id=document.id,
        document_url=_listing_url(document.id),
        status="manual_publish_requested",
        attempts=1,
    ).model_dump()


def _manual_publish_payload(run_id: str, document: Document, connection: dict[str, Any]) -> dict[str, Any]:
    topic = _manual_publish_topic(document)
    listing = _manual_publish_listing(document)
    return _n8n_payload(
        run_id=run_id,
        tenant_id=document.tenant_id,
        profile_url="manual_publish",
        publish_mode="manual_publish",
        auto_publish_requested=True,
        manual_publish_requested=True,
        connection=connection,
        topics=[topic],
        listings=[listing],
    )


def _manual_publish_error(n8n_status: str) -> str:
    if n8n_status == "not_configured":
        return "Publishing workflow is not configured for this tenant."
    if n8n_status == "invalid_webhook_url":
        return "Publishing workflow URL is invalid."
    if n8n_status == "credentials_missing":
        return "Connect Stuvia credentials before publishing this document."
    return f"Publishing workflow failed: {n8n_status}"


def publish_stuvia_document(document_id: str, user: User) -> dict[str, Any]:
    with SessionLocal() as db:
        db_user = db.get(User, user.id)
        if not db_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        document = get_document(db, document_id, db_user)
        if document.target_platform != "Stuvia":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only Stuvia documents can be published to Stuvia.")

        connection = stuvia_connection_settings(db, document.tenant_id)
        webhook_url = str(connection.get("n8n_webhook_url") or "").strip()
        if not str(connection.get("stuvia_email") or "").strip() or not str(connection.get("stuvia_password_encrypted") or "").strip():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_manual_publish_error("credentials_missing"))

        run_id = f"manual-{uuid4()}"
        webhook_token = str(connection.get("n8n_webhook_token") or "").strip()
        publish_payload = _manual_publish_payload(run_id, document, connection)
        publisher_url = str(publish_payload.get("browser_publisher_url") or "").strip()
        if publisher_url:
            n8n_status = _send_browser_publisher_payload(publisher_url, _publisher_auth_token(connection), publish_payload)
        else:
            if not webhook_url:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_manual_publish_error("not_configured"))
            if not _valid_n8n_webhook_url(webhook_url):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_manual_publish_error("invalid_webhook_url"))
            n8n_status = _send_n8n_payload(webhook_url, webhook_token, publish_payload)
        if not n8n_status.startswith("sent:") and n8n_status != "publisher:queued":
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=_manual_publish_error(n8n_status))

        db.add(
            AuditLog(
                tenant_id=document.tenant_id,
                user_id=user.id,
                action="stuvia.manual_publish.requested",
                resource_type="document",
                resource_id=document.id,
                event_metadata={"n8n_status": n8n_status, "run_id": run_id},
            )
        )
        db.commit()

        return {
            "document_id": document.id,
            "status": "publish_requested",
            "message": "Publish request queued. The final Stuvia result will be recorded by the publisher callback.",
            "n8n_status": n8n_status,
        }


def accept_stuvia_publisher_handoff(payload: dict[str, Any]) -> dict[str, Any]:
    listings = payload.get("listings")
    if not isinstance(listings, list):
        listings = []

    accepted_documents = 0
    received_document_ids: list[str] = []
    with SessionLocal() as db:
        for listing in listings:
            if not isinstance(listing, dict):
                continue
            document_id = str(listing.get("document_id") or "").strip()
            if not document_id:
                continue
            received_document_ids.append(document_id)
            document = db.get(Document, document_id)
            if not document or document.target_platform != "Stuvia":
                continue
            db.add(
                AuditLog(
                    tenant_id=document.tenant_id,
                    user_id=None,
                    action="stuvia.publisher.handoff.accepted",
                    resource_type="document",
                    resource_id=document.id,
                    event_metadata={
                        "run_id": payload.get("run_id"),
                        "manual_publish_requested": bool(payload.get("manual_publish_requested")),
                        "auto_publish_requested": bool(payload.get("auto_publish_requested")),
                    },
                )
            )
            accepted_documents += 1
        db.commit()

    return {
        "ok": True,
        "status": "accepted",
        "run_id": str(payload.get("run_id") or "") or None,
        "received_listings": len(listings),
        "updated_documents": 0,
        "message": "Stuvia publisher handoff accepted by the StudyMint backend. Final status requires a publisher result callback.",
        "details": {
            "document_ids": received_document_ids,
            "accepted_documents": accepted_documents,
            "publisher": "backend_internal_handoff",
        },
    }


def _latest_document_content(document: Document) -> dict[str, Any]:
    latest = max(document.versions, key=lambda version: version.version_number, default=None)
    if latest and isinstance(latest.content, dict):
        return latest.content
    return {
        "title_page": document.title,
        "introduction": "",
        "sections": [],
        "key_points": [],
        "examples": [],
        "study_questions": [],
        "conclusion": "",
        "metadata": {},
        "question_bank": [],
    }


def _ensure_publisher_pdf(db: Any, document: Document, content: dict[str, Any]) -> str:
    filename = _document_pdf_filename(document)
    output_path = settings.export_dir_path / filename
    if not output_path.exists():
        settings.export_dir_path.mkdir(parents=True, exist_ok=True)
        render_study_document_pdf(content, document.template_id, output_path)

    export = db.scalar(select(PdfExport).where(PdfExport.document_id == document.id).order_by(PdfExport.created_at.desc()).limit(1))
    if export is None:
        db.add(
            PdfExport(
                tenant_id=document.tenant_id,
                document_id=document.id,
                status=PdfExportStatus.COMPLETED.value,
                pdf_url=f"{settings.PDF_EXPORT_BASE_URL}/{filename}",
                renderer="simple_pdf_stuvia_publisher",
            )
        )
    document.status = DocumentStatus.PDF_READY.value
    db.commit()
    return f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}{settings.PDF_EXPORT_BASE_URL}/{filename}"


def publisher_document_package(document_id: str, tenant_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if not document or document.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found for this tenant")
        if document.target_platform != "Stuvia":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only Stuvia documents can be published")

        content = _latest_document_content(document)
        pdf_url = _ensure_publisher_pdf(db, document, content)
        sections = content.get("sections") if isinstance(content.get("sections"), list) else []
        question_bank = content.get("question_bank") if isinstance(content.get("question_bank"), list) else []
        key_points = content.get("key_points") if isinstance(content.get("key_points"), list) else []
        metadata = content.get("metadata") if isinstance(content.get("metadata"), dict) else {}

        return {
            "document_id": document.id,
            "tenant_id": document.tenant_id,
            "title": document.title,
            "subject": document.subject,
            "education_level": document.education_level,
            "document_type": document.document_type,
            "output_language": document.output_language,
            "length": document.length,
            "template_id": document.template_id,
            "pdf_url": pdf_url,
            "document_url": _listing_url(document.id),
            "introduction": str(content.get("introduction") or "")[:1500],
            "section_titles": [str(section.get("title") or "")[:180] for section in sections if isinstance(section, dict)][:20],
            "key_points": [str(item)[:240] for item in key_points][:12],
            "question_count": len(question_bank),
            "metadata": metadata,
        }


def accept_stuvia_publish_results(payload: dict[str, Any]) -> dict[str, Any]:
    raw_results = payload.get("results")
    results = raw_results if isinstance(raw_results, list) else []
    updated_documents = 0

    with SessionLocal() as db:
        for result in results:
            if not isinstance(result, dict):
                continue
            document_id = str(result.get("document_id") or "").strip()
            if not document_id:
                continue
            document = db.get(Document, document_id)
            if not document or document.target_platform != "Stuvia":
                continue

            result_status = str(result.get("status") or "").strip().lower()
            published = result_status in PUBLISH_MARKETPLACE_READY_STATUSES
            if published:
                document.status = DocumentStatus.MARKETPLACE_READY.value
                updated_documents += 1

            db.add(
                AuditLog(
                    tenant_id=document.tenant_id,
                    user_id=None,
                    action="stuvia.publish.result",
                    resource_type="document",
                    resource_id=document.id,
                    event_metadata={
                        "run_id": payload.get("run_id"),
                        "status": result.get("status"),
                        "stuvia_url": result.get("stuvia_url"),
                        "error": result.get("error"),
                        "listing": result.get("listing"),
                    },
                )
            )
        db.commit()

    _merge_publish_results_into_run(payload.get("run_id"), results)

    return {
        "ok": True,
        "status": "accepted",
        "run_id": str(payload.get("run_id") or "") or None,
        "received_results": len(results),
        "updated_documents": updated_documents,
    }


def _n8n_handoff_succeeded(payload: StuviaAgentRunCreate, n8n_status: str) -> bool:
    if payload.publish_mode == "drafts_only":
        return n8n_status == "drafts_only"
    return n8n_status.startswith("sent:") or n8n_status == "publisher:queued"


def _n8n_handoff_failure_message(payload: StuviaAgentRunCreate, n8n_status: str) -> str:
    if n8n_status == "not_configured":
        return "Documents were generated, but the publishing workflow is not configured for this tenant."
    if n8n_status == "invalid_webhook_url":
        return "Documents were generated, but the publishing workflow URL is invalid."
    if n8n_status == "auto_publish_disabled":
        return "Documents were generated, but auto-publish is not enabled in the Stuvia integration settings."
    return f"Documents were generated, but the publishing workflow failed: {n8n_status}"


def run_stuvia_agent(run_id: str, payload: StuviaAgentRunCreate, user_id: str) -> None:
    try:
        with SessionLocal() as db:
            user = db.get(User, user_id)
            tenant_id = user.tenant_id if user else ""
        if not tenant_id:
            raise RuntimeError("Requesting user no longer exists")

        _ensure_generation_configured()
        _update_run(run_id, status="RUNNING", stage="ranking_topics", message="Selecting unused topics from the cached Stuvia topic pool.", progress=12)
        profile_url = _validate_stuvia_profile_url(payload.profile_url)

        topics = _topics_from_cache_or_scrape(run_id, tenant_id, profile_url, payload)

        _update_run(run_id, stage="generating_documents", message="Generating review-ready Stuvia drafts.", progress=38)
        listings = _generate_documents(run_id, payload, user_id, topics)
        successful = [listing for listing in listings if listing["status"] != "failed"]
        if not successful:
            raise RuntimeError("No documents were generated successfully.")
        with SessionLocal() as db:
            remember_stuvia_topics(db, tenant_id, _topics_for_successful_listings(topics, successful))

        _update_run(run_id, stage="packaging_listings", message="Packaging listing metadata for review.", progress=86, listings=listings)
        n8n_status = _send_to_n8n(run_id, payload, topics, listings, tenant_id)
        if not _n8n_handoff_succeeded(payload, n8n_status):
            message = _n8n_handoff_failure_message(payload, n8n_status)
            _update_run(
                run_id,
                status="FAILED",
                stage="failed",
                message=message,
                error=message,
                progress=100,
                n8n_status=n8n_status,
                listings=listings,
            )
            return

        if payload.publish_mode == "n8n_auto_publish":
            _update_run(
                run_id,
                status="RUNNING",
                stage="n8n_review",
                message="Background publisher is signing in to Stuvia and submitting the generated documents.",
                progress=94,
                n8n_status=n8n_status,
            )
            return

        _update_run(run_id, stage="n8n_review", message="Background publishing handoff complete.", progress=94, n8n_status=n8n_status)
        _update_run(run_id, status="COMPLETED", stage="completed", message="Agent run complete. Documents are ready for review.", progress=100)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "Stuvia agent failed"
        _update_run(run_id, status="FAILED", stage="failed", message=detail, error=detail, progress=100)
    except Exception as exc:
        message = f"Stuvia agent failed: {exc}"
        _update_run(run_id, status="FAILED", stage="failed", message=message, error=message, progress=100)
