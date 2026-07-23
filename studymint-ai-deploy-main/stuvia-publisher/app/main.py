from __future__ import annotations

import asyncio
import json
import hashlib
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError, async_playwright


class Settings:
    backend_base_url = os.getenv("BACKEND_BASE_URL", "http://backend:8000").rstrip("/")
    shared_token = os.getenv("N8N_STUVIA_WEBHOOK_TOKEN", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_api_base_url = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    openai_model = os.getenv("OPENAI_FAST_MODEL") or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    openai_timeout_seconds = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "90"))
    stuvia_login_url = os.getenv("STUVIA_LOGIN_URL", "https://www.stuvia.com/login")
    stuvia_upload_url = os.getenv("STUVIA_UPLOAD_URL", "https://www.stuvia.com/upload")
    dry_run = os.getenv("STUVIA_PUBLISHER_DRY_RUN", "false").lower() in {"1", "true", "yes", "on"}
    headless = os.getenv("STUVIA_PUBLISHER_HEADLESS", "true").lower() not in {"0", "false", "no", "off"}
    browser_user_agent = os.getenv(
        "STUVIA_PUBLISHER_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    )
    browser_locale = os.getenv("STUVIA_PUBLISHER_LOCALE", "en-US")
    browser_timezone = os.getenv("STUVIA_PUBLISHER_TIMEZONE", "America/New_York")
    default_price = float(os.getenv("STUVIA_DEFAULT_PRICE", "9.99"))
    min_price = float(os.getenv("STUVIA_MIN_PRICE", "4.99"))
    max_price = float(os.getenv("STUVIA_MAX_PRICE", "24.99"))
    navigation_timeout_ms = int(os.getenv("STUVIA_PUBLISHER_NAVIGATION_TIMEOUT_MS", "30000"))
    form_timeout_ms = int(os.getenv("STUVIA_PUBLISHER_FORM_TIMEOUT_MS", "10000"))
    listing_timeout_seconds = int(os.getenv("STUVIA_PUBLISHER_LISTING_TIMEOUT_SECONDS", "150"))
    filestack_timeout_seconds = int(os.getenv("STUVIA_PUBLISHER_FILESTACK_TIMEOUT_SECONDS", "45"))
    screenshot_dir = Path(os.getenv("STUVIA_PUBLISHER_SCREENSHOT_DIR", "/tmp/stuvia-publisher"))
    session_dir = Path(os.getenv("STUVIA_PUBLISHER_SESSION_DIR", "/app/sessions"))


settings = Settings()
app = FastAPI(title="StudyMint Stuvia Publisher", version="0.1.0")

INSTITUTION_FIELD_SELECTORS = [
    "#studyInstitution",
    "select[name='studyInstitution']",
    "input[name='studyInstitution']",
    "input[id*='institution' i]",
    "input[placeholder*='Stanford' i]",
    "input[placeholder*='School' i]",
    "input[placeholder*='university' i]",
]
STUDY_FIELD_SELECTORS = [
    "#studyEducation",
    "input[name='studyEducation']",
    "input[id*='education' i]",
    "input[placeholder*='study' i]",
    "input[placeholder*='major' i]",
    "input[placeholder*='Nursing' i]",
    "input[placeholder*='Business Economics' i]",
]
COURSE_FIELD_SELECTORS = [
    "#studyCourse",
    "input[name='studyCourse']",
    "input[id*='course' i]",
    "input[placeholder*='ECO' i]",
    "input[placeholder*='Course code' i]",
]
COURSE_CODE_FIELD_SELECTORS = [
    "#studyCourse",
    "input[name='studyCourse']",
    "input[id*='course' i]",
    "input[placeholder*='Course code' i]",
    "input[placeholder*='ECO' i]",
]
FILE_INPUT_SELECTORS = [
    "#fsp-fileUpload",
    "input[type='file']",
    "input[accept*='pdf' i]",
    "input[name*='file' i]",
    "input[id*='file' i]",
    "input[class*='file' i]",
]
FILE_READY_SELECTORS = [
    "#fsp-fileUpload",
    "input[type='file']",
]


class PublishListing(BaseModel):
    title: str = ""
    topic: str = ""
    document_id: str | None = None
    document_url: str | None = None
    status: str = ""


class PublishRequest(BaseModel):
    run_id: str | None = None
    tenant_id: str | None = None
    credential_lookup_url: str = ""
    listings: list[PublishListing] = Field(default_factory=list)
    topics: list[dict[str, Any]] = Field(default_factory=list)
    manual_publish_requested: bool = False
    auto_publish_requested: bool = False
    posting_policy: str = ""


def _require_token(authorization: str | None) -> None:
    if not settings.shared_token:
        return
    if authorization != f"Bearer {settings.shared_token}":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid publisher token")


def _json_request(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 60) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if settings.shared_token:
        headers["Authorization"] = f"Bearer {settings.shared_token}"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _download_file(url: str, output_path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "StudyMint-Stuvia-Publisher/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        output_path.write_bytes(response.read())


def _clean_text(value: Any, *, max_length: int = 1000) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:max_length].rstrip()


def _text_haystack(*values: Any) -> str:
    return " ".join(_clean_text(value, max_length=500) for value in values if _clean_text(value, max_length=500))


def _safe_title(value: str) -> str:
    cleaned = _clean_text(value, max_length=150)
    cleaned = re.sub(r"\b(?:100\s*%|guaranteed|verified answers?|actual exam|instant download)\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -|")
    return cleaned or "Study Guide and Practice Questions"


def _price_for_document(document: dict[str, Any]) -> float:
    question_count = int(document.get("question_count") or 0)
    doc_type = str(document.get("document_type") or "").lower()
    length = str(document.get("length") or "").lower()
    price = settings.default_price
    if question_count >= 180:
        price = 18.99
    elif question_count >= 100:
        price = 14.99
    elif question_count >= 50:
        price = 11.99
    elif "question" in doc_type or "exam" in doc_type:
        price = 9.99
    elif length == "long":
        price = 12.99
    return round(min(max(price, settings.min_price), settings.max_price), 2)


def _fallback_listing(document: dict[str, Any], listing: PublishListing) -> dict[str, Any]:
    title = _safe_title(document.get("title") or listing.title)
    subject = _clean_text(document.get("subject") or listing.topic, max_length=120)
    doc_type = _clean_text(document.get("document_type"), max_length=80)
    level = _clean_text(document.get("education_level"), max_length=80)
    question_count = int(document.get("question_count") or 0)
    section_titles = document.get("section_titles") if isinstance(document.get("section_titles"), list) else []
    key_points = document.get("key_points") if isinstance(document.get("key_points"), list) else []
    includes = []
    if question_count:
        includes.append(f"{question_count} practice questions")
    if section_titles:
        includes.append("organized topic sections")
    if key_points:
        includes.append("key review points")
    if not includes:
        includes.append("structured study content")
    description = (
        f"{title} is a {doc_type or 'study'} resource for {subject or 'course review'}"
        f"{' at ' + level if level else ''}. It includes {', '.join(includes)} and is formatted for efficient revision, "
        "self-checking, and exam preparation. Use it alongside your course materials and instructor guidance."
    )
    tags = [subject, doc_type, level, "study guide", "practice questions", "exam prep"]
    return {
        "title": title,
        "description": description[:1800],
        "price": _price_for_document(document),
        "tags": [tag for tag in dict.fromkeys(_clean_text(tag, max_length=40) for tag in tags) if tag][:10],
        "category": "Nursing" if re.search(r"\b(nurs|nursing|hesi|nclex|medical|pharmacology|health)\b", subject, re.I) else "Study guides",
        "course": subject,
        "school": level,
        "language": document.get("output_language") or "English",
    }


def _extract_output_text(response_payload: dict[str, Any]) -> str:
    if isinstance(response_payload.get("output_text"), str):
        return response_payload["output_text"]
    parts: list[str] = []
    for item in response_payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def _json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("No JSON object found")


def _openai_listing(document: dict[str, Any], listing: PublishListing) -> dict[str, Any] | None:
    if not settings.openai_api_key:
        return None
    prompt = {
        "document": document,
        "listing": listing.model_dump(),
        "requirements": [
            "Create SEO metadata for a Stuvia marketplace listing.",
            "Do not claim verified, guaranteed, official, actual exam, or 100% correctness.",
            "Title max 150 characters. Description 700-1600 characters.",
            "Return JSON only with title, description, price, tags, category, course, school, language.",
            f"Price must be between {settings.min_price} and {settings.max_price}.",
        ],
    }
    body = {
        "model": settings.openai_model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "You write accurate, SEO-optimized marketplace metadata for original study documents.",
                    }
                ],
            },
            {"role": "user", "content": [{"type": "input_text", "text": json.dumps(prompt, ensure_ascii=False)}]},
        ],
        "max_output_tokens": 1400,
    }
    request = urllib.request.Request(
        f"{settings.openai_api_base_url}/responses",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.openai_timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
        parsed = _json_from_text(_extract_output_text(raw))
    except Exception:
        return None
    fallback = _fallback_listing(document, listing)
    title = _safe_title(parsed.get("title") or fallback["title"])
    description = _clean_text(parsed.get("description") or fallback["description"], max_length=1800)
    price = parsed.get("price", fallback["price"])
    try:
        price = round(min(max(float(price), settings.min_price), settings.max_price), 2)
    except (TypeError, ValueError):
        price = fallback["price"]
    tags = parsed.get("tags") if isinstance(parsed.get("tags"), list) else fallback["tags"]
    return {
        **fallback,
        "title": title,
        "description": description,
        "price": price,
        "tags": [tag for tag in (_clean_text(tag, max_length=40) for tag in tags) if tag][:10],
        "category": _clean_text(parsed.get("category") or fallback["category"], max_length=80),
        "course": _clean_text(parsed.get("course") or fallback["course"], max_length=120),
        "school": _clean_text(parsed.get("school") or fallback["school"], max_length=120),
        "language": _clean_text(parsed.get("language") or fallback["language"], max_length=40),
    }


def _listing_metadata(document: dict[str, Any], listing: PublishListing) -> dict[str, Any]:
    return _openai_listing(document, listing) or _fallback_listing(document, listing)


async def _click_if_visible(page: Page, pattern: str, *, timeout: int = 2500) -> bool:
    locators = [
        page.get_by_role("button", name=re.compile(pattern, re.I)),
        page.get_by_text(re.compile(pattern, re.I)),
    ]
    for locator in locators:
        try:
            await locator.first.click(timeout=timeout)
            return True
        except Exception:
            continue
    return False


async def _click_control_if_visible(page: Page, pattern: str, *, timeout: int = 2500) -> bool:
    locators = [
        page.get_by_role("button", name=re.compile(pattern, re.I)),
        page.get_by_role("link", name=re.compile(pattern, re.I)),
    ]
    for locator in locators:
        try:
            await locator.first.click(timeout=timeout)
            return True
        except Exception:
            continue
    return False


async def _click_visible_enabled_selector(page: Page, selectors: list[str], *, timeout: int = 4000) -> bool:
    for selector in selectors:
        controls = page.locator(selector)
        try:
            count = await controls.count()
        except Exception:
            continue
        for index in range(count):
            control = controls.nth(index)
            try:
                if not await control.is_visible(timeout=300):
                    continue
                if not await control.is_enabled(timeout=300):
                    continue
                await control.click(timeout=timeout)
                return True
            except Exception:
                continue
    return False


async def _dismiss_popups(page: Page) -> None:
    for pattern in (r"accept all|accept cookies|allow all", r"got it|close"):
        await _click_control_if_visible(page, pattern, timeout=1200)


async def _fill_field(page: Page, names: list[str], value: Any, *, textarea: bool = False) -> bool:
    text = str(value if value is not None else "").strip()
    if not text:
        return False
    tag = "textarea" if textarea else "input, textarea"
    for name in names:
        pattern = re.compile(name, re.I)
        try:
            await page.get_by_label(pattern).first.fill(text, timeout=2500)
            return True
        except Exception:
            pass
        selectors = [
            f"{tag}[name*='{name}' i]",
            f"{tag}[id*='{name}' i]",
            f"{tag}[placeholder*='{name}' i]",
        ]
        for selector in selectors:
            try:
                await page.locator(selector).first.fill(text, timeout=2500)
                return True
            except Exception:
                continue
    return False


async def _fill_by_type(page: Page, input_type: str, value: str, *, timeout: int = 3500) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    controls = page.locator(f"input[type='{input_type}']")
    try:
        count = await controls.count()
    except Exception:
        return False
    for index in range(count):
        control = controls.nth(index)
        try:
            if not await control.is_visible(timeout=300):
                continue
            if not await control.is_enabled(timeout=300):
                continue
            await control.fill(text, timeout=timeout)
            return True
        except Exception:
            continue
    return False


async def _capture_debug_screenshot(page: Page, label: str) -> str:
    settings.screenshot_dir.mkdir(parents=True, exist_ok=True)
    safe_label = re.sub(r"[^a-z0-9_-]+", "-", label.lower()).strip("-") or "stuvia-debug"
    screenshot = settings.screenshot_dir / f"{safe_label}.png"
    await page.screenshot(path=str(screenshot), full_page=True)
    return str(screenshot)


async def _assert_stuvia_page_available(page: Page, label: str) -> None:
    try:
        body_text = (await page.locator("body").inner_text(timeout=5000)).lower()
    except Exception:
        body_text = ""
    blocked = (
        ("403 error" in body_text and "cloudfront" in body_text)
        or ("request blocked" in body_text and "cloudfront" in body_text)
    )
    if blocked:
        screenshot = await _capture_debug_screenshot(page, label)
        raise RuntimeError(
            "Stuvia/CloudFront blocked the automated browser session before the login form loaded. "
            f"Screenshot: {screenshot}"
        )


async def _input_descriptor(locator: Any) -> str:
    try:
        descriptor = await locator.evaluate(
            """el => [
                el.getAttribute('name'),
                el.getAttribute('id'),
                el.getAttribute('placeholder'),
                el.getAttribute('autocomplete'),
                el.getAttribute('aria-label'),
                el.getAttribute('type'),
                ...(el.labels ? Array.from(el.labels).map(label => label.innerText) : [])
            ].filter(Boolean).join(' ')"""
        )
        return str(descriptor or "").lower()
    except Exception:
        return ""


async def _fill_first_visible_input(
    page: Page,
    value: str,
    hints: list[str],
    *,
    excluded_hints: list[str] | None = None,
    timeout: int = 2500,
) -> bool:
    text = str(value or "").strip()
    if not text:
        return False

    controls = page.locator("input:not([type='hidden']), textarea")
    try:
        count = await controls.count()
    except Exception:
        return False

    excluded_hints = excluded_hints or []
    visible_indexes: list[int] = []
    hint_pattern = re.compile("|".join(re.escape(hint) for hint in hints), re.I) if hints else None
    excluded_pattern = re.compile("|".join(re.escape(hint) for hint in excluded_hints), re.I) if excluded_hints else None

    for index in range(count):
        control = controls.nth(index)
        try:
            if not await control.is_visible(timeout=300):
                continue
        except Exception:
            continue
        visible_indexes.append(index)
        descriptor = await _input_descriptor(control)
        if excluded_pattern and excluded_pattern.search(descriptor):
            continue
        if hint_pattern and hint_pattern.search(descriptor):
            try:
                await control.fill(text, timeout=timeout)
                return True
            except Exception:
                continue

    for index in visible_indexes:
        control = controls.nth(index)
        descriptor = await _input_descriptor(control)
        if excluded_pattern and excluded_pattern.search(descriptor):
            continue
        try:
            await control.fill(text, timeout=timeout)
            return True
        except Exception:
            continue

    return False


async def _wait_for_any_field(page: Page, selectors: list[str], *, timeout: int = 10000) -> bool:
    deadline = time.monotonic() + (timeout / 1000)
    while time.monotonic() < deadline:
        for selector in selectors:
            try:
                await page.locator(selector).first.wait_for(state="visible", timeout=500)
                return True
            except Exception:
                continue
        await page.wait_for_timeout(250)
    return False


async def _select_or_fill(page: Page, names: list[str], value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    for name in names:
        pattern = re.compile(name, re.I)
        try:
            select = page.get_by_label(pattern).first
            await select.select_option(label=text, timeout=2000)
            return True
        except Exception:
            pass
    return await _fill_field(page, names, text)


def _upload_course_text(metadata: dict[str, Any]) -> str:
    haystack = _text_haystack(
        metadata.get("course"),
        metadata.get("title"),
        metadata.get("description"),
        metadata.get("category"),
    )
    course_code = re.search(
        r"\b(?:NUR|NURS|NR|NRNP|HESI|NCLEX|BIOS|BIO|BIOL|CHEM|PSYC|PSYCH|MATH|ECO|ECON|BUS|ACC|ACCT|ENG|ENGL|HIST|SOC|PHARM|MED|HLTH|MSN|DNP)\s*[-/]?\s*\d{2,5}[A-Z]?\b",
        haystack,
        re.I,
    )
    if course_code:
        return re.sub(r"\s+", " ", course_code.group(0).upper().replace("-", " ")).strip()

    candidates = [
        metadata.get("course"),
        metadata.get("category"),
        metadata.get("title"),
    ]
    for candidate in candidates:
        text = _clean_text(candidate, max_length=80)
        text = re.split(
            r"\b(?:exam|preparation|prep|study|guide|questions?|answers?|resources?|certification|objective|assessment|test|practice|review|latest|update|download|bundle|package)\b",
            text,
            maxsplit=1,
            flags=re.I,
        )[0]
        text = re.sub(r"[^A-Za-z0-9 &/-]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip(" -/&")
        if len(text.split()) > 4:
            text = " ".join(text.split()[:4])
        if text:
            return _clean_text(text, max_length=45)
    return _upload_course_fallback_text(metadata)


def _upload_course_fallback_text(metadata: dict[str, Any]) -> str:
    configured = _clean_text(os.getenv("STUVIA_DEFAULT_COURSE", ""), max_length=45)
    if configured:
        return configured

    haystack = _text_haystack(
        metadata.get("course"),
        metadata.get("title"),
        metadata.get("description"),
        metadata.get("category"),
    )
    if re.search(r"\b(nurs|nursing|hesi|nclex|medical|pharmacology|health)\b", haystack, re.I):
        return "Nursing"
    if re.search(r"\b(psych|psychology)\b", haystack, re.I):
        return "Psychology"
    if re.search(r"\b(network|software|programming|computer|cyber)\b", haystack, re.I):
        return "Computer Networking"
    if re.search(r"\b(business|accounting|finance|economic)\b", haystack, re.I):
        return "Business"
    return "General Studies"


def _upload_study_text(metadata: dict[str, Any]) -> str:
    configured = _clean_text(
        os.getenv("STUVIA_DEFAULT_STUDY", "") or os.getenv("STUVIA_DEFAULT_COURSE", ""),
        max_length=60,
    )
    if configured:
        return configured

    haystack = _text_haystack(
        metadata.get("course"),
        metadata.get("title"),
        metadata.get("description"),
        metadata.get("category"),
    )
    if re.search(r"\b(nurs|nursing|hesi|nclex|medical|pharmacology|health)\b", haystack, re.I):
        return "Nursing"
    if re.search(r"\b(psych|psychology)\b", haystack, re.I):
        return "Psychology"
    if re.search(r"\b(network|software|programming|computer|cyber)\b", haystack, re.I):
        return "Computer Science"
    if re.search(r"\b(business|accounting|finance|economic)\b", haystack, re.I):
        return "Business"
    return _upload_course_fallback_text(metadata)


def _upload_course_code_text(metadata: dict[str, Any]) -> str:
    configured = _clean_text(os.getenv("STUVIA_DEFAULT_COURSE_CODE", ""), max_length=30)
    if configured:
        return configured
    haystack = _text_haystack(
        metadata.get("course"),
        metadata.get("title"),
        metadata.get("description"),
        metadata.get("category"),
    )
    course_code = re.search(
        r"\b(?:NUR|NURS|NR|NRNP|HESI|NCLEX|BIOS|BIO|BIOL|CHEM|PSYC|PSYCH|MATH|ECO|ECON|BUS|ACC|ACCT|ENG|ENGL|HIST|SOC|PHARM|MED|HLTH|MSN|DNP)\s*[-/]?\s*\d{2,5}[A-Z]?\b",
        haystack,
        re.I,
    )
    if not course_code:
        if re.search(r"\bhesi\b", haystack, re.I):
            return "HESI"
        if re.search(r"\bnclex\b", haystack, re.I):
            return "NCLEX"
        if re.search(r"\bati\b", haystack, re.I):
            return "ATI"
        if re.search(r"\bkaplan\b", haystack, re.I):
            return "KAPLAN"
        if re.search(r"\b(nurs|nursing|medical|pharmacology|health)\b", haystack, re.I):
            return "NUR 101"
        if re.search(r"\b(psych|psychology)\b", haystack, re.I):
            return "PSYC 101"
        if re.search(r"\b(network|software|programming|computer|cyber)\b", haystack, re.I):
            return "CS 101"
        if re.search(r"\b(business|accounting|finance|economic)\b", haystack, re.I):
            return "BUS 101"
        return "GEN 101"
    return re.sub(r"\s+", " ", course_code.group(0).upper().replace("-", " ")).strip()


def _upload_course_code_candidates(metadata: dict[str, Any]) -> list[str]:
    haystack = _text_haystack(
        metadata.get("course"),
        metadata.get("title"),
        metadata.get("description"),
        metadata.get("category"),
    )
    candidates = [
        _upload_course_code_text(metadata),
        os.getenv("STUVIA_DEFAULT_COURSE_CODE", ""),
    ]
    if re.search(r"\bhesi\b", haystack, re.I):
        candidates.extend(["HESI", "NUR 101", "NURS 101"])
    if re.search(r"\bnclex\b", haystack, re.I):
        candidates.extend(["NCLEX", "NUR 101", "NURS 101"])
    if re.search(r"\bati\b", haystack, re.I):
        candidates.extend(["ATI", "NUR 101", "NURS 101"])
    if re.search(r"\bkaplan\b", haystack, re.I):
        candidates.extend(["KAPLAN", "NUR 101", "NURS 101"])
    if re.search(r"\b(nurs|nursing|medical|pharmacology|health)\b", haystack, re.I):
        candidates.extend(["NUR 101", "NURS 101"])
    if re.search(r"\b(psych|psychology)\b", haystack, re.I):
        candidates.extend(["PSYC 101", "PSY 101"])
    if re.search(r"\b(network|software|programming|computer|cyber)\b", haystack, re.I):
        candidates.extend(["CS 101", "CIS 101"])
    if re.search(r"\b(business|accounting|finance|economic)\b", haystack, re.I):
        candidates.extend(["BUS 101", "ACC 101", "ECON 101"])
    candidates.extend(["NUR 101", "GEN 101"])

    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        text = _clean_text(candidate, max_length=30).upper()
        if not text:
            continue
        key = re.sub(r"[^A-Z0-9]+", "", text)
        if key and key not in seen:
            unique.append(text)
            seen.add(key)
    return unique


def _upload_institution_text(metadata: dict[str, Any]) -> str:
    haystack = " ".join(
        _clean_text(metadata.get(key), max_length=200)
        for key in ("title", "description", "course", "school", "category")
    )
    known_patterns = [
        (r"\bgalen college(?: of nursing)?\b", "Galen College of Nursing"),
        (r"\bwalden university\b", "Walden University"),
        (r"\bwestern governors university\b|\bwgu\b", "Western Governors University"),
        (r"\bchamberlain university\b", "Chamberlain University"),
        (r"\brasmussen university\b", "Rasmussen University"),
        (r"\bherzing university\b", "Herzing University"),
    ]
    for pattern, institution in known_patterns:
        if re.search(pattern, haystack, re.I):
            return institution

    configured = _clean_text(os.getenv("STUVIA_DEFAULT_INSTITUTION", ""), max_length=80)
    if configured:
        return configured

    school = _clean_text(metadata.get("school"), max_length=80)
    if school and not re.search(r"\b(college|university|school|undergraduate|graduate|nursing|exam|prep)\b", school, re.I):
        return school

    return "Galen College of Nursing"


async def _click_first_existing(page: Page, selectors: list[str], *, timeout: int = 3000, force: bool = False) -> bool:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if not await locator.count():
                continue
            await locator.click(timeout=timeout, force=force)
            return True
        except Exception:
            continue
    return False


async def _has_any_selector(page: Page, selectors: list[str]) -> bool:
    for selector in selectors:
        try:
            if await page.locator(selector).count():
                return True
        except Exception:
            continue
    return False


async def _has_visible_selector(page: Page, selectors: list[str]) -> bool:
    for selector in selectors:
        controls = page.locator(selector)
        try:
            count = await controls.count()
        except Exception:
            continue
        for index in range(count):
            try:
                if await controls.nth(index).is_visible(timeout=250):
                    return True
            except Exception:
                continue
    return False


async def _wait_for_any_selector(page: Page, selectors: list[str], *, timeout: int = 30000) -> bool:
    deadline = time.monotonic() + (timeout / 1000)
    while time.monotonic() < deadline:
        if await _has_any_selector(page, selectors):
            return True
        await page.wait_for_timeout(500)
    return False


async def _wait_for_visible_selector(page: Page, selectors: list[str], *, timeout: int = 30000) -> bool:
    deadline = time.monotonic() + (timeout / 1000)
    while time.monotonic() < deadline:
        if await _has_visible_selector(page, selectors):
            return True
        await page.wait_for_timeout(500)
    return False


async def _has_us_college_course_form(page: Page) -> bool:
    return await _has_visible_selector(page, INSTITUTION_FIELD_SELECTORS) and await _has_visible_selector(page, COURSE_CODE_FIELD_SELECTORS)


async def _has_supported_upload_context_form(page: Page) -> bool:
    return await _has_visible_selector(page, STUDY_FIELD_SELECTORS) or await _has_us_college_course_form(page)


async def _wait_for_supported_upload_context_form(page: Page, *, timeout: int = 30000) -> bool:
    deadline = time.monotonic() + (timeout / 1000)
    while time.monotonic() < deadline:
        if await _has_supported_upload_context_form(page):
            return True
        await page.wait_for_timeout(500)
    return False


async def _first_available_locator(page: Page, selectors: list[str]) -> Any | None:
    fallback: Any | None = None
    for selector in selectors:
        controls = page.locator(selector)
        try:
            count = await controls.count()
            if not count:
                continue
        except Exception:
            continue
        for index in range(count):
            locator = controls.nth(index)
            if fallback is None:
                fallback = locator
            try:
                if await locator.is_visible(timeout=250) and await locator.is_enabled(timeout=250):
                    return locator
            except Exception:
                continue
    return fallback


async def _select_best_native_option(locator: Any, value: str) -> bool:
    text = _clean_text(value, max_length=80).lower()
    try:
        selected = await locator.evaluate(
            """(select, wanted) => {
                const normalize = value => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
                const target = normalize(wanted);
                const options = Array.from(select.options || []).filter(option => option.value && !option.disabled);
                if (!options.length) return null;
                let match = options.find(option => normalize(option.textContent) === target || normalize(option.value) === target);
                if (!match) match = options.find(option => normalize(option.textContent).includes(target) || target.includes(normalize(option.textContent)));
                if (!match) return null;
                select.value = match.value;
                select.dispatchEvent(new Event('input', { bubbles: true }));
                select.dispatchEvent(new Event('change', { bubbles: true }));
                return { value: match.value, text: match.textContent };
            }""",
            text,
        )
    except Exception:
        return False
    return bool(selected)


async def _click_matching_autocomplete_option(page: Page, value: str, *, allow_add_new: bool = False) -> bool:
    text = _clean_text(value, max_length=80)
    if not text:
        return False
    selectors = [
        ".autocomplete-suggestion",
        ".autocomplete-suggestions li",
        ".tt-menu .tt-suggestion",
        ".typeahead .tt-suggestion",
        ".ui-menu-item",
        ".selectize-dropdown-content [data-selectable]",
        ".dropdown-menu li",
        ".dropdown-menu a",
        ".dropdown-menu button",
        "[class*='autocomplete'] li",
        "[class*='suggestion']",
        "[class*='dropdown'] [role='option']",
        "[class*='result']",
        "[role='option']",
        ".select2-results__option",
    ]
    if allow_add_new:
        selectors.append("a.autocomplete-add-new.confirm")
    try:
        clicked = await page.evaluate(
            """({ selectors, wanted, allowAddNew }) => {
                const normalize = value => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
                const target = normalize(wanted);
                const visible = el => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style && style.visibility !== 'hidden' && style.display !== 'none' && box.width > 0 && box.height > 0;
                };
                const options = selectors.flatMap(selector => Array.from(document.querySelectorAll(selector)))
                    .filter((el, index, all) => all.indexOf(el) === index)
                    .filter(el => visible(el) && !el.disabled)
                    .map(el => ({ el, text: String(el.innerText || el.textContent || el.value || '').replace(/\\s+/g, ' ').trim() }))
                    .filter(item => item.text);
                const exact = options.find(item => normalize(item.text) === target);
                const contains = options.find(item => {
                    const optionText = normalize(item.text);
                    return optionText.includes(target) || (target.includes(optionText) && optionText.length >= 4);
                });
                const addNew = allowAddNew ? options.find(item => /add|new|create/i.test(item.text)) : null;
                const chosen = exact || contains || addNew;
                if (!chosen) return false;
                chosen.el.scrollIntoView({ block: 'center', inline: 'center' });
                chosen.el.click();
                return true;
            }""",
            {"selectors": selectors, "wanted": text, "allowAddNew": allow_add_new},
        )
    except Exception:
        clicked = False
    if clicked:
        await page.wait_for_timeout(900)
    return bool(clicked)


async def _clear_existing_upload_state(page: Page) -> None:
    for selector in (
        ".remove-upload-file",
        "buttton.cta-remove-itembox, .cta-remove-itembox, .doc-upload-item .fa-trash-alt, [class*='trash']",
    ):
        for _ in range(8):
            controls = page.locator(selector)
            try:
                if not await controls.count():
                    break
                await controls.first.click(timeout=2500, force=True)
                await page.wait_for_timeout(700)
            except Exception:
                break


def _target_upload_country() -> str:
    return _clean_text(os.getenv("STUVIA_DEFAULT_COUNTRY", "United States"), max_length=80) or "United States"


def _is_united_states_country_value(value: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "", str(value or "").lower())
    return normalized in {"279", "us", "usa", "unitedstates", "unitedstatesofamerica"}


async def _select_native_country(page: Page, country: str) -> bool:
    try:
        selected = await page.evaluate(
            """country => {
                const normalize = value => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
                const target = normalize(country);
                const selects = Array.from(document.querySelectorAll('select'));
                for (const select of selects) {
                    const descriptor = [select.name, select.id, select.getAttribute('aria-label'), select.placeholder].filter(Boolean).join(' ');
                    const options = Array.from(select.options || []);
                    const match = options.find(option => normalize(option.textContent) === target || normalize(option.value) === target);
                    if (!match) continue;
                    if (!/country|upload/i.test(descriptor) && !options.some(option => /united states/i.test(option.textContent || ''))) continue;
                    select.value = match.value;
                    select.dispatchEvent(new Event('input', { bubbles: true }));
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }
                return false;
            }""",
            country,
        )
    except Exception:
        selected = False
    if selected:
        await page.wait_for_timeout(800)
    return bool(selected)


async def _open_country_picker(page: Page) -> bool:
    if await _click_visible_enabled_selector(
        page,
        [
            "#upload-country-select",
            "[data-target*='country' i]",
            "[data-toggle*='country' i]",
            "button:has-text('Change country')",
            "a:has-text('Change country')",
            "[role='button']:has-text('Change country')",
            "button:has-text('Country')",
            "a:has-text('Country')",
        ],
        timeout=2500,
    ):
        return True
    return (
        await _click_control_if_visible(page, r"change\s+country|country", timeout=2500)
        or await _click_if_visible(page, r"change\s+country|country", timeout=2500)
    )


async def _set_upload_country(page: Page) -> None:
    country = _target_upload_country()
    try:
        country_value = await page.locator("#uploadCountry").first.get_attribute("value", timeout=800)
    except Exception:
        country_value = None
    if country.lower() == "united states" and _is_united_states_country_value(country_value):
        return

    if await _select_native_country(page, country):
        return

    try:
        if not await _open_country_picker(page):
            return
        await page.wait_for_timeout(700)
        if await _select_native_country(page, country):
            return
        field = await _first_available_locator(
            page,
            [
                "input[placeholder*='country' i]",
                "input[name*='country' i]",
                "input[id*='country' i]",
                ".select2-search__field",
            ],
        )
        if field is not None:
            try:
                await field.fill(country, timeout=2500)
                await page.wait_for_timeout(700)
            except Exception:
                pass
        if not await _click_matching_autocomplete_option(page, country):
            await page.get_by_text(re.compile(rf"^\s*{re.escape(country)}\s*$", re.I)).first.click(timeout=3500, force=True)
        await page.wait_for_timeout(1500)
    except Exception:
        return


async def _click_course_at_college_upload_type(page: Page) -> bool:
    direct_locators = [
        page.locator("#user-type-select li.radio-listitem").filter(has_text=re.compile(r"^\s*Course at College/University\s*$", re.I)).first,
        page.locator("li.radio-listitem").filter(has_text=re.compile(r"^\s*Course at College/University\s*$", re.I)).first,
        page.get_by_text(re.compile(r"^\s*Course at College/University\s*$", re.I)).first,
    ]
    for locator in direct_locators:
        try:
            if not await locator.count():
                continue
            await locator.scroll_into_view_if_needed(timeout=2500)
            box = await locator.bounding_box(timeout=2500)
            if box and box["width"] > 0 and box["height"] > 0:
                await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            else:
                await locator.click(timeout=3500, force=True)
            await page.wait_for_timeout(1200)
            return True
        except Exception:
            continue

    try:
        point = await page.evaluate(
            """() => {
                const visible = el => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style && style.visibility !== 'hidden' && style.display !== 'none' && box.width > 0 && box.height > 0;
                };
                const isDisabled = el => el.disabled || el.getAttribute('aria-disabled') === 'true';
                const controls = Array.from(document.querySelectorAll(
                    'button, a, label, [role="button"], input[type="radio"], input[type="checkbox"], li, div, section'
                ));
                const candidates = controls
                    .filter(el => visible(el) && !isDisabled(el))
                    .map(el => ({
                        el,
                        text: String(el.innerText || el.value || el.textContent || '').replace(/\\s+/g, ' ').trim()
                    }))
                    .filter(item => item.text && item.text.length < 220);
                const isCourseOption = item => /course\\s+at\\s+college\\s*\\/\\s*university/i.test(item.text)
                    && !/exam|qualification|training|high school/i.test(item.text);
                const target = candidates.find(item => /^course\\s+at\\s+college\\s*\\/\\s*university$/i.test(item.text))
                    || candidates.find(isCourseOption)
                    || candidates.find(item => /college\\s*\\/\\s*university/i.test(item.text) && !/exam|qualification|training|high school/i.test(item.text));
                if (!target) return false;
                let clickable = target.el;
                if (!/^(BUTTON|A|LABEL|INPUT)$/i.test(clickable.tagName) && clickable.getAttribute('role') !== 'button') {
                    clickable = clickable.closest('li.radio-listitem, button, a, label, [role="button"], [class*="option"], [class*="choice"], [class*="type"], [class*="card"]') || clickable;
                }
                clickable.scrollIntoView({ block: 'center', inline: 'center' });
                if (clickable.tagName === 'INPUT' && /checkbox|radio/i.test(clickable.type || '')) {
                    clickable.checked = true;
                    clickable.dispatchEvent(new Event('input', { bubbles: true }));
                    clickable.dispatchEvent(new Event('change', { bubbles: true }));
                }
                const box = clickable.getBoundingClientRect();
                return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
            }"""
        )
    except Exception:
        point = None
    if point:
        try:
            await page.mouse.click(float(point["x"]), float(point["y"]))
        except Exception:
            return False
        await page.wait_for_timeout(1200)
        return True
    return False


async def _choose_upload_type(page: Page) -> None:
    if await _has_supported_upload_context_form(page):
        return
    if await _has_visible_selector(page, INSTITUTION_FIELD_SELECTORS + COURSE_FIELD_SELECTORS):
        try:
            await page.get_by_text(re.compile(r"^Back to first step$", re.I)).first.click(timeout=2500, force=True)
            await page.wait_for_timeout(1200)
        except Exception:
            pass
    if await _has_supported_upload_context_form(page):
        return

    clicked_course_type = (
        await _click_course_at_college_upload_type(page)
        or await _click_if_visible(page, r"course at college/university|college/university", timeout=3500)
        or await _click_control_if_visible(page, r"course at college/university|college/university", timeout=3500)
        or await _click_text_with_js(page, r"course at college/university|college/university")
    )
    if clicked_course_type:
        if await _wait_for_supported_upload_context_form(page, timeout=18000):
            return
        screenshot = await _capture_debug_screenshot(page, "stuvia-upload-type-click-did-not-open-form")
        raise RuntimeError(f"Stuvia Course at College/University option was clicked but the upload form did not open. Screenshot: {screenshot}")

    radios = [
        "input[name='user-types'][value='stu']",
    ]
    for selector in radios:
        locator = page.locator(selector).first
        try:
            if not await locator.count():
                continue
            await locator.check(timeout=3000, force=True)
            if await _wait_for_supported_upload_context_form(page, timeout=30000):
                return
            await _click_course_at_college_upload_type(page)
            if await _wait_for_supported_upload_context_form(page, timeout=20000):
                return
        except Exception:
            continue


async def _select_stuvia_autocomplete(
    page: Page,
    selectors: str | list[str],
    value: str,
    *,
    allow_add_new: bool = False,
    require_match: bool = False,
) -> bool:
    text = _clean_text(value, max_length=50)
    if not text:
        return False
    field_selectors = [selectors] if isinstance(selectors, str) else selectors
    field = await _first_available_locator(page, field_selectors)
    if field is None:
        return False
    try:
        tag_name = await field.evaluate("el => el.tagName.toLowerCase()")
    except Exception:
        tag_name = ""
    if tag_name == "select":
        selected = await _select_best_native_option(field, text)
        if selected:
            await page.wait_for_timeout(2500)
        return selected
    try:
        await field.fill(text, timeout=5000)
    except Exception:
        return False
    await page.wait_for_timeout(1500)

    clicked = await _click_matching_autocomplete_option(page, text, allow_add_new=allow_add_new)
    if not clicked and not require_match:
        try:
            await field.press("Enter", timeout=2000)
            await page.wait_for_timeout(600)
            await field.press("Tab", timeout=2000)
            clicked = True
        except Exception:
            clicked = False
    await page.wait_for_timeout(2200)
    await _confirm_add_new_study(page)
    return clicked


async def _select_upload_institution(page: Page, preferred: str) -> str:
    candidates: list[str] = []
    for value in (
        preferred,
        os.getenv("STUVIA_DEFAULT_INSTITUTION", ""),
        "Galen College of Nursing",
        "Chamberlain University",
        "Walden University",
        "Western Governors University",
        "Rasmussen University",
        "Herzing University",
    ):
        text = _clean_text(value, max_length=80)
        if text and text.lower() not in {candidate.lower() for candidate in candidates}:
            candidates.append(text)

    for candidate in candidates:
        if await _select_stuvia_autocomplete(page, INSTITUTION_FIELD_SELECTORS, candidate, require_match=True):
            return candidate
    for candidate in candidates[:2]:
        if await _select_stuvia_autocomplete(page, INSTITUTION_FIELD_SELECTORS, candidate, require_match=False):
            return candidate
    return ""


async def _select_upload_course_code(page: Page, metadata: dict[str, Any]) -> str:
    for candidate in _upload_course_code_candidates(metadata):
        if not await _has_visible_selector(page, COURSE_CODE_FIELD_SELECTORS):
            return ""
        await _select_stuvia_autocomplete(page, COURSE_CODE_FIELD_SELECTORS, candidate)
        if await _dismiss_invalid_course_dialog(page):
            continue
        if await _wait_for_file_picker(page, timeout=6500):
            return candidate
    return ""


async def _confirm_add_new_study(page: Page) -> bool:
    try:
        body_text = (await page.locator("body").inner_text(timeout=1500)).lower()
    except Exception:
        body_text = ""
    if "unknown on stuvia" not in body_text and "add this study" not in body_text:
        return False
    clicked = (
        await _click_control_if_visible(page, r"yes,\s*add this study|add this study", timeout=2500)
        or await _click_if_visible(page, r"yes,\s*add this study|add this study", timeout=2500)
    )
    if clicked:
        await page.wait_for_timeout(1000)
    return clicked


async def _dismiss_invalid_course_dialog(page: Page) -> bool:
    try:
        body_text = (await page.locator("body").inner_text(timeout=1500)).lower()
    except Exception:
        body_text = ""
    if "course name you provided is not valid" not in body_text:
        return False
    if not await _click_control_if_visible(page, r"^ok$", timeout=2500):
        await _click_if_visible(page, r"^ok$", timeout=2500)
    await page.wait_for_timeout(700)
    return True


async def _wait_for_file_picker(page: Page, *, timeout: int = 70000) -> bool:
    deadline = time.monotonic() + (timeout / 1000)
    last_finalize_at = 0.0
    while time.monotonic() < deadline:
        if await _has_any_selector(page, FILE_READY_SELECTORS):
            return True
        try:
            body_text = (await page.locator("body").inner_text(timeout=1200)).lower()
        except Exception:
            body_text = ""
        if "drag your file" in body_text or "choose your file" in body_text:
            return True
        if "add this study" in body_text or "unknown on stuvia" in body_text:
            await _confirm_add_new_study(page)
        if "course name you provided is not valid" in body_text:
            return False
        if time.monotonic() - last_finalize_at > 4:
            last_finalize_at = time.monotonic()
            try:
                await page.keyboard.press("Tab")
            except Exception:
                pass
        await page.wait_for_timeout(800)
    return False


async def _prepare_upload_context(page: Page, metadata: dict[str, Any]) -> None:
    await _clear_existing_upload_state(page)
    await _set_upload_country(page)
    await _choose_upload_type(page)

    if not await _wait_for_supported_upload_context_form(page, timeout=30000):
        screenshot = await _capture_debug_screenshot(page, "stuvia-upload-type-missing")
        raise RuntimeError(f"Stuvia Course at College/University upload form did not load. Screenshot: {screenshot}")
    await _clear_existing_upload_state(page)

    institution = _upload_institution_text(metadata)
    study = _upload_study_text(metadata)
    course_code = _upload_course_code_text(metadata)

    selected_institution = await _select_upload_institution(page, institution)
    if not selected_institution:
        screenshot = await _capture_debug_screenshot(page, "stuvia-upload-institution-not-selected")
        raise RuntimeError(f"Stuvia did not accept a school/university selection. Screenshot: {screenshot}")

    if await _has_visible_selector(page, STUDY_FIELD_SELECTORS):
        if not await _has_visible_selector(page, STUDY_FIELD_SELECTORS):
            await _choose_upload_type(page)
        if await _has_visible_selector(page, STUDY_FIELD_SELECTORS):
            await _select_stuvia_autocomplete(page, STUDY_FIELD_SELECTORS, study, allow_add_new=True)
        if course_code and await _has_visible_selector(page, COURSE_CODE_FIELD_SELECTORS):
            await _select_stuvia_autocomplete(page, COURSE_CODE_FIELD_SELECTORS, course_code)
        if await _dismiss_invalid_course_dialog(page):
            await _select_stuvia_autocomplete(page, STUDY_FIELD_SELECTORS, _upload_study_text(metadata), allow_add_new=True)
            await _dismiss_invalid_course_dialog(page)
    elif await _has_visible_selector(page, COURSE_CODE_FIELD_SELECTORS):
        await _select_upload_course_code(page, metadata)

    if not await _wait_for_file_picker(page):
        screenshot = await _capture_debug_screenshot(page, "stuvia-upload-file-picker-not-ready")
        raise RuntimeError(f"Stuvia course selection did not reveal the file upload picker. Screenshot: {screenshot}")


async def _set_file(page: Page, file_path: Path) -> None:
    for selector in FILE_INPUT_SELECTORS:
        try:
            await page.locator(selector).last.set_input_files(str(file_path), timeout=5000)
            return
        except Exception:
            continue

    await _click_if_visible(page, r"upload|select file|choose file|browse|document", timeout=2500)
    for selector in FILE_INPUT_SELECTORS:
        try:
            await page.locator(selector).last.set_input_files(str(file_path), timeout=7000)
            return
        except Exception:
            continue

    screenshot = await _capture_debug_screenshot(page, "stuvia-upload-file-input-missing")
    try:
        page_title = await page.title()
    except Exception:
        page_title = ""
    raise RuntimeError(
        "Could not find the Stuvia file upload field "
        f"at {page.url}. Page title: {page_title or 'unknown'}. Screenshot: {screenshot}"
    )


async def _wait_for_selected_upload_file(page: Page, file_path: Path) -> None:
    expected_name = file_path.name
    deadline = time.monotonic() + min(settings.filestack_timeout_seconds, 25)
    while time.monotonic() < deadline:
        try:
            selected_text = await page.locator(".lists-preview, .fsp-footer, body").first.inner_text(timeout=1200)
        except Exception:
            selected_text = ""
        if expected_name in selected_text:
            return
        if await page.locator(".remove-upload-file").count():
            return
        if re.search(r"Selected Files:\s*[1-9]", selected_text, re.I):
            return
        await page.wait_for_timeout(700)

    screenshot = await _capture_debug_screenshot(page, "stuvia-upload-file-not-selected")
    raise RuntimeError(f"Stuvia did not confirm selected file {expected_name}. Screenshot: {screenshot}")


async def _click_filestack_button(page: Page, label: str, *, timeout: int = 5000) -> bool:
    locator = page.locator(".fsp-button, button, a, [role='button'], [class*='button']").filter(
        has_text=re.compile(rf"^\s*{re.escape(label)}\s*$", re.I)
    )
    try:
        count = await locator.count()
    except Exception:
        return False
    for index in range(count - 1, -1, -1):
        button = locator.nth(index)
        try:
            class_name = str(await button.get_attribute("class", timeout=500) or "")
            if "disabled" in class_name.lower():
                continue
            await button.click(timeout=timeout, force=True)
            return True
        except Exception:
            continue
    return False


async def _filestack_container_visible(page: Page) -> bool:
    for selector in (
        ".fsp-modal",
        ".fsp-picker",
        ".fsp-content",
        ".fsp-footer",
        ".fsp-source-list",
        ".fsp-drop-pane",
        ".fsp-picker__body",
    ):
        locator = page.locator(selector)
        try:
            count = await locator.count()
        except Exception:
            continue
        for index in range(count):
            try:
                if await locator.nth(index).is_visible(timeout=250):
                    return True
            except Exception:
                continue
    return False


async def _filestack_upload_action_visible(page: Page) -> bool:
    locator = page.locator(".fsp-button, button, a, [role='button'], [class*='button']").filter(
        has_text=re.compile(r"^\s*Upload\s*$", re.I)
    )
    try:
        count = await locator.count()
    except Exception:
        return False
    for index in range(count):
        control = locator.nth(index)
        try:
            class_name = str(await control.get_attribute("class", timeout=400) or "")
            if "disabled" in class_name.lower():
                continue
            if await control.is_visible(timeout=250) and await control.is_enabled(timeout=250):
                return True
        except Exception:
            continue
    return False


async def _upload_documents_action_available(page: Page) -> bool:
    selectors = [
        ".cta-submit-form:has-text('Upload Documents')",
        ".button:has-text('Upload Documents')",
        ".btn:has-text('Upload Documents')",
        "[class*='cta']:has-text('Upload Documents')",
        "[class*='button']:has-text('Upload Documents')",
        "a.cta-submit-form:has-text('Upload Documents')",
        "a.btn:has-text('Upload Documents')",
        "a.button:has-text('Upload Documents')",
        "button:has-text('Upload Documents')",
        "input[type='submit'][value*='Upload Documents' i]",
        "[role='button']:has-text('Upload Documents')",
    ]
    for selector in selectors:
        controls = page.locator(selector)
        try:
            count = await controls.count()
        except Exception:
            continue
        for index in range(count):
            control = controls.nth(index)
            try:
                if await control.is_visible(timeout=250) and await control.is_enabled(timeout=250):
                    return True
            except Exception:
                continue
    try:
        control = page.get_by_role("button", name=re.compile(r"^\s*upload documents\s*$", re.I)).first
        if await control.count() and await control.is_visible(timeout=250) and await control.is_enabled(timeout=250):
            return True
    except Exception:
        pass
    return False


async def _click_filestack_upload_action(page: Page) -> bool:
    if await _click_visible_enabled_selector(
        page,
        [
            ".fsp-button-upload:not(.fsp-button--disabled)",
        ],
        timeout=3500,
    ):
        return True
    if await _click_filestack_button(page, "Upload", timeout=6000):
        return True
    try:
        clicked = await page.evaluate(
            """() => {
                const visible = el => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style && style.visibility !== 'hidden' && style.display !== 'none' && box.width > 0 && box.height > 0;
                };
                const controls = Array.from(document.querySelectorAll('.fsp-button, button, a, [role="button"], [class*="button"]'));
                const target = controls.reverse().find(el => /^\\s*Upload\\s*$/i.test(el.innerText || el.value || el.textContent || '') && visible(el));
                if (!target) return false;
                target.scrollIntoView({ block: 'center', inline: 'center' });
                target.click();
                return true;
            }"""
        )
    except Exception:
        clicked = False
    return bool(clicked)


async def _initial_upload_ready(page: Page, file_path: Path) -> bool:
    try:
        body_text = await page.locator("body").inner_text(timeout=1500)
    except Exception:
        body_text = ""
    normalized_body = body_text.lower()
    expected_name = file_path.name.lower()

    file_is_listed = expected_name in normalized_body
    try:
        file_is_listed = file_is_listed or bool(
            await page.locator(".remove-upload-file, .doc-upload-item, .doc-upload-field, [class*='upload-item'], [class*='uploaded-file']").count()
        )
    except Exception:
        pass
    upload_documents_ready = await _upload_documents_action_available(page)
    if file_is_listed and upload_documents_ready:
        return True

    if await _filestack_upload_action_visible(page):
        return False

    try:
        if await page.locator(".fsp-modal").first.is_visible(timeout=300):
            return False
    except Exception:
        pass

    ready_selectors = [
        ".remove-upload-file",
        ".doc-upload-item",
        ".doc-upload-field",
        "[class*='upload-item']",
        "[class*='uploaded-file']",
        ".cta-submit-form:has-text('Upload Documents')",
        "a:has-text('Upload Documents')",
        "button:has-text('Upload Documents')",
    ]
    try:
        if await page.locator(", ".join(ready_selectors)).count() and "upload documents" in normalized_body:
            return True
    except Exception:
        pass
    if expected_name in normalized_body and "upload documents" in normalized_body and "filestack" not in normalized_body:
        return True
    return False


async def _confirm_filestack_upload(page: Page, file_path: Path) -> None:
    await _wait_for_selected_upload_file(page, file_path)
    deadline = time.monotonic() + settings.filestack_timeout_seconds
    clicked_once = False
    last_click_at = 0.0
    while time.monotonic() < deadline:
        if await _initial_upload_ready(page, file_path):
            return
        if time.monotonic() - last_click_at >= 4:
            clicked = await _click_filestack_upload_action(page)
            if not clicked and await _click_filestack_button(page, "View/Edit Selected", timeout=3000):
                await page.wait_for_timeout(800)
                clicked = await _click_filestack_upload_action(page)
            if clicked:
                clicked_once = True
                last_click_at = time.monotonic()
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except PlaywrightTimeoutError:
                    pass
                await page.wait_for_timeout(1800)
                continue
        await page.wait_for_timeout(800)

    if not clicked_once:
        screenshot = await _capture_debug_screenshot(page, "stuvia-filestack-upload-button-missing")
        raise RuntimeError(f"Could not find the Stuvia FileStack Upload button for {file_path.name}. Screenshot: {screenshot}")
    screenshot = await _capture_debug_screenshot(page, "stuvia-filestack-upload-not-confirmed")
    raise RuntimeError(f"Stuvia FileStack upload did not complete for {file_path.name}. Screenshot: {screenshot}")


async def _click_upload_documents_action(page: Page) -> bool:
    selectors = [
        ".cta-submit-form:has-text('Upload Documents')",
        ".button:has-text('Upload Documents')",
        ".btn:has-text('Upload Documents')",
        "[class*='cta']:has-text('Upload Documents')",
        "[class*='button']:has-text('Upload Documents')",
        "a.cta-submit-form:has-text('Upload Documents')",
        "a.btn:has-text('Upload Documents')",
        "a.button:has-text('Upload Documents')",
        "button:has-text('Upload Documents')",
        "input[type='submit'][value*='Upload Documents' i]",
        "[role='button']:has-text('Upload Documents')",
    ]
    if await _click_visible_enabled_selector(page, selectors, timeout=5000):
        return True
    try:
        locator = page.get_by_role("button", name=re.compile(r"^\s*upload documents\s*$", re.I)).first
        await locator.scroll_into_view_if_needed(timeout=2500)
        await locator.click(timeout=3500, force=True)
        return True
    except Exception:
        pass
    try:
        clicked = await page.evaluate(
            """() => {
                const visible = el => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style && style.visibility !== 'hidden' && style.display !== 'none' && box.width > 0 && box.height > 0;
                };
                const controls = Array.from(document.querySelectorAll('button,input,[role="button"],a.cta-submit-form,a.btn,a.button,.cta-submit-form,.btn,.button,[class*="button"],[class*="cta"]'));
                const actionable = el => {
                    const tag = String(el.tagName || '').toLowerCase();
                    const klass = String(el.className || '').toLowerCase();
                    return tag === 'button' || tag === 'input' || el.getAttribute('role') === 'button' || /cta|btn|button|submit/.test(klass);
                };
                const target = controls.find(el => /upload\\s+documents/i.test(el.innerText || el.value || el.textContent || '') && visible(el) && actionable(el));
                if (!target) return false;
                target.scrollIntoView({ block: 'center', inline: 'center' });
                target.click();
                return true;
            }"""
        )
    except Exception:
        clicked = False
    if clicked:
        await page.wait_for_timeout(800)
    return bool(clicked)


async def _check_required_boxes(page: Page) -> None:
    try:
        original_work_box = page.locator("#aggreement-did-it-myself").first
        if await original_work_box.count():
            await original_work_box.check(timeout=2000, force=True)
    except Exception:
        pass

    try:
        walden_box = page.locator("#walden-agreement").first
        if await walden_box.count() and await walden_box.is_visible(timeout=500):
            await walden_box.check(timeout=1500, force=True)
    except Exception:
        pass

    labels = [
        r"terms",
        r"conditions",
        r"original",
        r"copyright",
        r"permission",
        r"i agree",
        r"i confirm",
        r"made by myself",
        r"rights of third parties",
        r"literal copy",
    ]
    for label in labels:
        try:
            box = page.get_by_label(re.compile(label, re.I)).first
            if await box.count():
                await box.check(timeout=1500, force=True)
        except Exception:
            continue


async def _login(page: Page, email: str, password: str) -> None:
    response = await page.goto(settings.stuvia_login_url, wait_until="domcontentloaded", timeout=settings.navigation_timeout_ms)
    try:
        await page.wait_for_load_state("networkidle", timeout=7000)
    except PlaywrightTimeoutError:
        pass
    if response and response.status == 403:
        screenshot = await _capture_debug_screenshot(page, "stuvia-cloudfront-login-block")
        raise RuntimeError(
            "Stuvia/CloudFront returned HTTP 403 before the login form loaded. "
            f"Screenshot: {screenshot}"
        )
    await _assert_stuvia_page_available(page, "stuvia-cloudfront-login-block")
    await _dismiss_popups(page)
    email_filled = (
        await _fill_first_visible_input(page, email, ["auth_email", "email", "e-mail", "username", "login"])
        or await _fill_by_type(page, "email", email)
        or await _fill_field(page, ["email", "e-mail"], email)
    )
    if not email_filled:
        screenshot = await _capture_debug_screenshot(page, "stuvia-login-email-field")
        raise RuntimeError(f"Could not find the Stuvia email field. Screenshot: {screenshot}")
    if not await _click_visible_enabled_selector(
        page,
        [
            "#email-step-form button[type='submit']",
            "form:has(#auth_email) button[type='submit']",
            "button:has-text('Continue with email')",
        ],
    ) and not await _click_control_if_visible(page, r"continue with email|continue|next"):
        await page.keyboard.press("Enter")
    await _wait_for_any_field(
        page,
        [
            "input[type='password']",
            "input[name*='password' i]",
            "input[id*='password' i]",
            "input[autocomplete*='password' i]",
        ],
        timeout=15000,
    )
    password_filled = (
        await _fill_first_visible_input(page, password, ["password", "passcode"], excluded_hints=["email", "e-mail"])
        or await _fill_by_type(page, "password", password)
        or await _fill_field(page, ["password", "passcode"], password)
    )
    if not password_filled:
        screenshot = await _capture_debug_screenshot(page, "stuvia-login-password-field")
        raise RuntimeError(f"Could not find the Stuvia password field. Screenshot: {screenshot}")
    if not await _click_visible_enabled_selector(
        page,
        [
            "#login-form button[type='submit']",
            "form:has(#password-login) button[type='submit']",
            "button:has-text('Log in')",
        ],
    ) and not await _click_control_if_visible(page, r"^log in$|^login$|sign in"):
        await page.keyboard.press("Enter")
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeoutError:
        pass
    await _dismiss_popups(page)
    body_text = (await page.locator("body").inner_text(timeout=5000)).lower()
    if "captcha" in body_text or "verification code" in body_text or "two-factor" in body_text:
        raise RuntimeError("Stuvia requested captcha, verification, or MFA. Manual account intervention is required.")
    if re.search(r"email and password.*did not match|incorrect|invalid", body_text):
        raise RuntimeError("Stuvia rejected the configured email or password.")
    if "/login" in page.url and "password" in body_text and "log in" in body_text:
        raise RuntimeError("Stuvia login did not complete.")


async def _fill_listing_metadata(page: Page, metadata: dict[str, Any]) -> None:
    await _fill_field(page, ["title", "document title", "name"], metadata["title"])
    await _fill_field(page, ["description", "summary", "content"], metadata["description"], textarea=True)
    await _fill_field(page, ["price", "selling price", "amount"], f"{float(metadata['price']):.2f}")
    await _select_or_fill(page, ["course", "subject", "module"], metadata.get("course") or "")
    await _select_or_fill(page, ["school", "education", "institution", "university"], metadata.get("school") or "")
    await _select_or_fill(page, ["category", "type", "document type"], metadata.get("category") or "")
    await _select_or_fill(page, ["language"], metadata.get("language") or "English")
    tags = metadata.get("tags") if isinstance(metadata.get("tags"), list) else []
    if tags:
        await _fill_field(page, ["tags", "keywords"], ", ".join(tags))


async def _body_text(page: Page, *, timeout: int = 2500) -> str:
    try:
        return await page.locator("body").inner_text(timeout=timeout)
    except Exception:
        return ""


async def _settle_after_click(page: Page, *, timeout: int = 7000) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except PlaywrightTimeoutError:
        pass
    await page.wait_for_timeout(700)
    await _dismiss_popups(page)


async def _click_text_with_js(page: Page, pattern: str) -> bool:
    try:
        return bool(
            await page.evaluate(
                """pattern => {
                    const regex = new RegExp(pattern, 'i');
                    const visible = el => {
                        const style = window.getComputedStyle(el);
                        const box = el.getBoundingClientRect();
                        return style && style.visibility !== 'hidden' && style.display !== 'none' && box.width > 0 && box.height > 0;
                    };
                    const controls = Array.from(document.querySelectorAll('button, a, input, [role="button"], [role="option"], li, .button, .btn, [class*="button"], [class*="btn"], [class*="option"]'));
                    const target = controls.find(el => {
                        const text = String(el.innerText || el.value || el.textContent || '').replace(/\\s+/g, ' ').trim();
                        return text && text.length < 160 && regex.test(text) && visible(el) && !el.disabled;
                    });
                    if (!target) return false;
                    target.scrollIntoView({ block: 'center', inline: 'center' });
                    target.click();
                    return true;
                }""",
                pattern,
            )
        )
    except Exception:
        return False


async def _click_wizard_action(page: Page, pattern: str, *, timeout: int = 4000) -> bool:
    return (
        await _click_control_if_visible(page, pattern, timeout=timeout)
        or await _click_if_visible(page, pattern, timeout=timeout)
        or await _click_text_with_js(page, pattern)
    )


async def _click_save_next_step(page: Page) -> bool:
    if await _click_visible_enabled_selector(
        page,
        [
            "button:has-text('Save & next step')",
            "a:has-text('Save & next step')",
            "[role='button']:has-text('Save & next step')",
            ".button:has-text('Save & next step')",
            ".btn:has-text('Save & next step')",
            "button:has-text('Save and next step')",
            "a:has-text('Save and next step')",
            "input[type='submit'][value*='Save' i]",
        ],
        timeout=5000,
    ):
        return True
    return await _click_wizard_action(page, r"save\s*(?:&|and)\s*next\s*step|next step|continue", timeout=4000)


async def _set_native_select_option(page: Page, label_patterns: list[str], option_patterns: list[str]) -> bool:
    payload = {"labels": label_patterns, "options": option_patterns}
    try:
        selected = await page.evaluate(
            """({ labels, options }) => {
                const labelRegexes = labels.map(pattern => new RegExp(pattern, 'i'));
                const optionRegexes = options.map(pattern => new RegExp(pattern, 'i'));
                const visible = el => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style && style.visibility !== 'hidden' && style.display !== 'none' && box.width > 0 && box.height > 0;
                };
                const textOf = el => String(el.innerText || el.textContent || el.value || '').replace(/\\s+/g, ' ').trim();
                const candidateSelects = [];
                const pushSelects = root => {
                    if (!root) return;
                    if (root.matches && root.matches('select') && visible(root)) candidateSelects.push(root);
                    for (const select of Array.from(root.querySelectorAll ? root.querySelectorAll('select') : [])) {
                        if (visible(select)) candidateSelects.push(select);
                    }
                };

                for (const label of Array.from(document.querySelectorAll('label, div, span, p, h1, h2, h3, h4'))) {
                    const labelText = textOf(label);
                    if (!labelText || labelText.length > 140 || !labelRegexes.some(regex => regex.test(labelText))) continue;
                    if (label.htmlFor) pushSelects(document.getElementById(label.htmlFor));
                    let root = label;
                    for (let depth = 0; root && root !== document.body && depth < 5; depth += 1, root = root.parentElement) {
                        pushSelects(root);
                    }
                }

                for (const select of Array.from(document.querySelectorAll('select'))) {
                    if (visible(select) && !candidateSelects.includes(select)) candidateSelects.push(select);
                }

                for (const select of candidateSelects) {
                    const option = Array.from(select.options || []).find(candidate => {
                        if (candidate.disabled) return false;
                        const optionText = textOf(candidate);
                        return optionRegexes.some(regex => regex.test(optionText));
                    });
                    if (!option) continue;
                    select.value = option.value;
                    select.dispatchEvent(new Event('input', { bubbles: true }));
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }
                return false;
            }""",
            payload,
        )
    except Exception:
        selected = False
    if selected:
        await page.wait_for_timeout(500)
    return bool(selected)


async def _open_labeled_control(page: Page, label_patterns: list[str]) -> bool:
    for pattern in label_patterns:
        try:
            control = page.get_by_label(re.compile(pattern, re.I)).first
            if await control.count():
                await control.scroll_into_view_if_needed(timeout=1500)
                await control.click(timeout=2500, force=True)
                return True
        except Exception:
            continue

    try:
        opened = await page.evaluate(
            """patterns => {
                const regexes = patterns.map(pattern => new RegExp(pattern, 'i'));
                const visible = el => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style && style.visibility !== 'hidden' && style.display !== 'none' && box.width > 0 && box.height > 0;
                };
                const textOf = el => String(el.innerText || el.textContent || el.value || '').replace(/\\s+/g, ' ').trim();
                const controlsFor = root => Array.from(root.querySelectorAll('select, input, textarea, button, [role="combobox"], [role="button"], .select2-selection, .selectize-input, [class*="select"], [class*="dropdown"]'));
                const labels = Array.from(document.querySelectorAll('label, div, span, p, h1, h2, h3, h4')).filter(el => {
                    const text = textOf(el);
                    return text && text.length < 140 && visible(el) && regexes.some(regex => regex.test(text));
                });
                for (const label of labels) {
                    if (label.htmlFor) {
                        const direct = document.getElementById(label.htmlFor);
                        if (direct && visible(direct) && !direct.disabled) {
                            direct.scrollIntoView({ block: 'center', inline: 'center' });
                            direct.click();
                            return true;
                        }
                    }
                    let root = label;
                    for (let depth = 0; root && root !== document.body && depth < 5; depth += 1, root = root.parentElement) {
                        const control = controlsFor(root).find(el => el !== label && visible(el) && !el.disabled);
                        if (control) {
                            control.scrollIntoView({ block: 'center', inline: 'center' });
                            control.click();
                            return true;
                        }
                    }
                }
                return false;
            }""",
            label_patterns,
        )
    except Exception:
        opened = False
    if opened:
        await page.wait_for_timeout(350)
    return bool(opened)


async def _click_option_text(page: Page, option_patterns: list[str]) -> bool:
    for pattern in option_patterns:
        locators = [
            page.get_by_role("option", name=re.compile(pattern, re.I)),
            page.get_by_role("menuitem", name=re.compile(pattern, re.I)),
            page.get_by_text(re.compile(pattern, re.I)),
        ]
        for locator in locators:
            try:
                await locator.first.scroll_into_view_if_needed(timeout=1200)
                await locator.first.click(timeout=2500, force=True)
                await page.wait_for_timeout(400)
                return True
            except Exception:
                continue
        if await _click_text_with_js(page, pattern):
            await page.wait_for_timeout(400)
            return True
    return False


async def _select_labeled_option(page: Page, label_patterns: list[str], option_patterns: list[str]) -> bool:
    if await _set_native_select_option(page, label_patterns, option_patterns):
        return True
    if not await _open_labeled_control(page, label_patterns):
        return False
    return await _click_option_text(page, option_patterns)


async def _choose_labeled_choice(page: Page, patterns: list[str]) -> bool:
    for pattern in patterns:
        try:
            control = page.get_by_label(re.compile(pattern, re.I)).first
            if await control.count():
                try:
                    await control.check(timeout=2500, force=True)
                except Exception:
                    await control.click(timeout=2500, force=True)
                await page.wait_for_timeout(350)
                return True
        except Exception:
            pass
        if await _click_if_visible(page, pattern, timeout=2500):
            await page.wait_for_timeout(350)
            return True
        if await _click_text_with_js(page, pattern):
            await page.wait_for_timeout(350)
            return True
    return False


def _document_type_candidates(metadata: dict[str, Any]) -> list[str]:
    configured = _clean_text(os.getenv("STUVIA_DEFAULT_DOCUMENT_TYPE", ""), max_length=80)
    haystack = _text_haystack(metadata.get("title"), metadata.get("description"), metadata.get("category"), metadata.get("course"))
    candidates: list[str] = []
    if configured:
        candidates.append(re.escape(configured))
    if re.search(r"\bcase\b", haystack, re.I):
        candidates.append(r"^case$")
    if re.search(r"\b(class notes?|lecture notes?|notes?)\b", haystack, re.I):
        candidates.append(r"class notes?")
    if re.search(r"\b(summary|summaries)\b", haystack, re.I):
        candidates.append(r"summar(?:y|ies)")
    candidates.extend([r"exam\s*\(elaborations?\)", r"exam", r"summary", r"class notes?"])
    return list(dict.fromkeys(candidates))


def _written_year_candidates(metadata: dict[str, Any]) -> list[str]:
    haystack = _text_haystack(metadata.get("title"), metadata.get("description"), metadata.get("course"))
    candidates = []
    for match in re.finditer(r"\b(20\d{2})\s*/\s*(20\d{2}|\d{2})\b", haystack):
        first = match.group(1)
        second = match.group(2)
        if len(second) == 2:
            second = first[:2] + second
        candidates.append(f"{first}/{second}")
    configured = _clean_text(os.getenv("STUVIA_DEFAULT_DOCUMENT_YEAR", ""), max_length=20)
    if configured:
        candidates.append(configured)
    candidates.extend(["2025/2026", "2024/2025", "2026/2027", "2023/2024"])
    return [re.escape(candidate) for candidate in dict.fromkeys(candidate for candidate in candidates if candidate)]


def _course_level_candidates() -> list[str]:
    configured = _clean_text(os.getenv("STUVIA_DEFAULT_COURSE_LEVEL", ""), max_length=30)
    candidates = [configured, "3rd year", "2nd year", "1st year", "4th year", "Bachelor"]
    return [re.escape(candidate) for candidate in dict.fromkeys(candidate for candidate in candidates if candidate)]


def _grade_candidates() -> list[str]:
    configured = _clean_text(os.getenv("STUVIA_DEFAULT_GRADE", ""), max_length=20)
    candidates = [configured, "A+", "A", "Pass"]
    return [re.escape(candidate) for candidate in dict.fromkeys(candidate for candidate in candidates if candidate)]


async def _fill_keywords(page: Page, metadata: dict[str, Any]) -> None:
    tags = metadata.get("tags") if isinstance(metadata.get("tags"), list) else []
    tags = [_clean_text(tag, max_length=40) for tag in tags if _clean_text(tag, max_length=40)]
    if not tags:
        return
    selectors = [
        "input[placeholder*='keyword' i]",
        "input[placeholder*='comma' i]",
        "input[name*='keyword' i]",
        "input[name*='tag' i]",
        "input[id*='keyword' i]",
        "input[id*='tag' i]",
    ]
    field = await _first_available_locator(page, selectors)
    if field is None:
        await _fill_field(page, ["keywords", "tags", "subjects"], ", ".join(tags[:6]))
        return
    for tag in tags[:6]:
        try:
            await field.fill(tag, timeout=1800)
            await field.press("Enter", timeout=1200)
            await page.wait_for_timeout(250)
        except Exception:
            try:
                await field.fill(", ".join(tags[:6]), timeout=1800)
            except Exception:
                pass
            return


async def _set_price(page: Page, price: Any) -> None:
    try:
        price_value = float(price)
    except (TypeError, ValueError):
        price_value = settings.default_price
    values = [f"{price_value:.2f}", f"{price_value:.2f}".replace(".", ",")]
    for value in values:
        if await _fill_field(page, ["price", "selling price", "amount"], value):
            return
    try:
        await page.evaluate(
            """values => {
                const visible = el => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style && style.visibility !== 'hidden' && style.display !== 'none' && box.width > 0 && box.height > 0;
                };
                const input = Array.from(document.querySelectorAll('input:not([type="hidden"])')).find(el => visible(el) && /price|amount|earning|sale/i.test([el.name, el.id, el.placeholder, el.getAttribute('aria-label')].filter(Boolean).join(' ')));
                if (!input) return false;
                input.value = values[0];
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }""",
            values,
        )
    except Exception:
        pass


async def _handle_document_information_step(page: Page, metadata: dict[str, Any]) -> None:
    await _select_labeled_option(page, [r"category", r"document type"], _document_type_candidates(metadata))
    await _choose_labeled_choice(page, [r"questions?\s*&\s*answers?", r"questions?\s+and\s+answers?"])
    await _select_labeled_option(page, [r"grade"], _grade_candidates())
    await _choose_labeled_choice(page, [r"no,\s*do not link a book", r"do not link a book"])
    await _select_labeled_option(page, [r"year", r"written"], _written_year_candidates(metadata))
    if not await _click_save_next_step(page):
        screenshot = await _capture_debug_screenshot(page, "stuvia-document-info-save-missing")
        raise RuntimeError(f"Could not save Stuvia document information. Screenshot: {screenshot}")
    await _settle_after_click(page)


async def _handle_course_information_step(page: Page, metadata: dict[str, Any]) -> None:
    course_code = re.search(r"\b[A-Z]{2,8}\s*[-/]?\s*\d{2,5}[A-Z]?\b", _text_haystack(metadata.get("title"), metadata.get("course")), re.I)
    if course_code:
        await _fill_field(page, ["course code", "course"], re.sub(r"\s+", " ", course_code.group(0).upper()).strip())
    await _select_labeled_option(page, [r"course level", r"select course level", r"level"], _course_level_candidates())
    if not await _click_save_next_step(page):
        screenshot = await _capture_debug_screenshot(page, "stuvia-course-info-save-missing")
        raise RuntimeError(f"Could not save Stuvia course information. Screenshot: {screenshot}")
    await _settle_after_click(page)


async def _handle_title_description_step(page: Page, metadata: dict[str, Any]) -> None:
    await _fill_keywords(page, metadata)
    await _fill_field(page, ["choose a title", "title", "document title", "name"], metadata["title"])
    await _fill_field(page, ["describe your document", "description", "summary"], metadata["description"], textarea=True)
    await _select_labeled_option(page, [r"language"], [re.escape(metadata.get("language") or "English"), r"English"])
    if not await _click_save_next_step(page):
        screenshot = await _capture_debug_screenshot(page, "stuvia-title-description-save-missing")
        raise RuntimeError(f"Could not save Stuvia title and description. Screenshot: {screenshot}")
    await _settle_after_click(page)


async def _handle_price_publish_step(page: Page, metadata: dict[str, Any]) -> dict[str, Any] | None:
    await _set_price(page, metadata.get("price"))
    if settings.dry_run:
        return {"status": "dry_run_ready", "stuvia_url": page.url}
    clicked = (
        await _click_visible_enabled_selector(
            page,
            [
                "button:has-text('Save and publish')",
                "a:has-text('Save and publish')",
                "[role='button']:has-text('Save and publish')",
                ".button:has-text('Save and publish')",
                ".btn:has-text('Save and publish')",
                "input[type='submit'][value*='publish' i]",
            ],
            timeout=5000,
        )
        or await _click_wizard_action(page, r"save\s*(?:and|&)\s*publish|publish", timeout=5000)
    )
    if not clicked:
        screenshot = await _capture_debug_screenshot(page, "stuvia-save-publish-missing")
        raise RuntimeError(f"Could not find Stuvia Save and publish button. Screenshot: {screenshot}")
    await _settle_after_click(page, timeout=12000)
    return None


def _stuvia_publish_confirmation(body_text: str) -> str | None:
    normalized = body_text.lower()
    if re.search(r"upload successful|successfully uploaded|published|now online|document is online|listing is live", normalized):
        return "published"
    if re.search(r"submitted|for review|thank you|saved", normalized):
        return "submitted_for_review"
    return None


def _stuvia_step_name(body_text: str) -> str:
    normalized = body_text.lower()
    if re.search(r"save and publish|earnings per sale", normalized):
        return "price"
    if re.search(r"choose a title that best describes|describe your document|name as many keywords", normalized):
        return "title"
    if re.search(r"select course level|what course code|when is the exam", normalized):
        return "course"
    if re.search(r"choose your document type|the document contains|what grade did you get|do you want to link a book|in which year is the document written", normalized):
        return "document"
    return "unknown"


async def _complete_describe_publish_wizard(page: Page, metadata: dict[str, Any]) -> dict[str, Any]:
    last_signature = ""
    stalled_steps = 0
    for _ in range(10):
        await _dismiss_popups(page)
        body_text = await _body_text(page, timeout=6000)
        confirmation = _stuvia_publish_confirmation(body_text)
        if confirmation:
            return {"status": confirmation, "stuvia_url": page.url}

        normalized = body_text.lower()
        if re.search(r"there (?:is|was).*error|please complete|required field|failed|invalid|could not|try again", normalized):
            screenshot = await _capture_debug_screenshot(page, "stuvia-wizard-form-error")
            raise RuntimeError(f"Stuvia reported a wizard form error. Screenshot: {screenshot}")

        step_name = _stuvia_step_name(body_text)
        signature = f"{page.url}|{step_name}|{normalized[:300]}"
        if signature == last_signature:
            stalled_steps += 1
        else:
            stalled_steps = 0
            last_signature = signature
        if stalled_steps >= 2:
            screenshot = await _capture_debug_screenshot(page, "stuvia-wizard-stalled")
            raise RuntimeError(f"Stuvia publishing wizard did not advance from {step_name}. Screenshot: {screenshot}")

        if step_name == "document":
            await _handle_document_information_step(page, metadata)
        elif step_name == "course":
            await _handle_course_information_step(page, metadata)
        elif step_name == "title":
            await _handle_title_description_step(page, metadata)
        elif step_name == "price":
            maybe_result = await _handle_price_publish_step(page, metadata)
            if maybe_result:
                return maybe_result
        else:
            await _fill_listing_metadata(page, metadata)
            await _check_required_boxes(page)
            if not await _click_save_next_step(page) and not await _click_wizard_action(page, r"continue|next|save|publish", timeout=3000):
                screenshot = await _capture_debug_screenshot(page, "stuvia-wizard-next-missing")
                raise RuntimeError(f"Could not find the next Stuvia wizard action. Screenshot: {screenshot}")
            await _settle_after_click(page)

    body_text = await _body_text(page, timeout=5000)
    confirmation = _stuvia_publish_confirmation(body_text)
    if confirmation:
        return {"status": confirmation, "stuvia_url": page.url}
    screenshot = await _capture_debug_screenshot(page, "stuvia-publish-unconfirmed")
    raise RuntimeError(f"Stuvia did not show a publish confirmation after completing the wizard. Screenshot: {screenshot}")


async def _advance_upload_steps(page: Page, metadata: dict[str, Any]) -> None:
    for _ in range(4):
        await _dismiss_popups(page)
        await _fill_listing_metadata(page, metadata)
        await _check_required_boxes(page)
        clicked = await _click_control_if_visible(page, r"next|continue|save draft|save and continue", timeout=1800)
        if not clicked:
            break
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except PlaywrightTimeoutError:
            pass
        await page.wait_for_timeout(500)


async def _submit_initial_upload_step(page: Page, file_path: Path, metadata: dict[str, Any]) -> None:
    await _prepare_upload_context(page, metadata)
    await _set_file(page, file_path)
    await _confirm_filestack_upload(page, file_path)
    await _check_required_boxes(page)
    clicked = await _click_upload_documents_action(page)
    if not clicked:
        screenshot = await _capture_debug_screenshot(page, "stuvia-upload-documents-button-missing")
        raise RuntimeError(f"Could not find Stuvia Upload Documents button. Screenshot: {screenshot}")
    try:
        await page.wait_for_load_state("networkidle", timeout=12000)
    except PlaywrightTimeoutError:
        pass
    await page.wait_for_timeout(1500)

    body_text = (await page.locator("body").inner_text(timeout=10000)).lower()
    if re.search(r"please select|required|could not|failed|invalid", body_text) and "describe documents" not in body_text:
        screenshot = await _capture_debug_screenshot(page, "stuvia-initial-upload-error")
        raise RuntimeError(f"Stuvia reported an error on the initial upload step. Screenshot: {screenshot}")


async def _publish_in_browser(page: Page, file_path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    response = await page.goto(settings.stuvia_upload_url, wait_until="domcontentloaded", timeout=settings.navigation_timeout_ms)
    if response and response.status == 403:
        screenshot = await _capture_debug_screenshot(page, "stuvia-cloudfront-upload-block")
        raise RuntimeError(
            "Stuvia/CloudFront returned HTTP 403 before the upload page loaded. "
            f"Screenshot: {screenshot}"
        )
    await _assert_stuvia_page_available(page, "stuvia-cloudfront-upload-block")
    await _dismiss_popups(page)
    if "/login" in page.url:
        raise RuntimeError("Stuvia redirected to login after authentication.")
    await _submit_initial_upload_step(page, file_path, metadata)
    return await _complete_describe_publish_wizard(page, metadata)


async def _new_browser_context(playwright: Any, storage_state_path: Path | None = None) -> tuple[Any, Any]:
    browser = await playwright.chromium.launch(
        headless=settings.headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ],
    )
    context_options: dict[str, Any] = {
        "accept_downloads": True,
        "viewport": {"width": 1440, "height": 1100},
        "screen": {"width": 1440, "height": 1100},
        "user_agent": settings.browser_user_agent,
        "locale": settings.browser_locale,
        "timezone_id": settings.browser_timezone,
        "color_scheme": "light",
        "device_scale_factor": 1,
        "extra_http_headers": {
            "Accept-Language": f"{settings.browser_locale},en;q=0.9",
            "DNT": "1",
        },
    }
    if storage_state_path and storage_state_path.exists():
        context_options["storage_state"] = str(storage_state_path)

    context = await browser.new_context(**context_options)
    await context.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
        window.chrome = window.chrome || { runtime: {} };
        """
    )
    return browser, context


def _tenant_id_from_request(request: PublishRequest) -> str:
    if request.tenant_id:
        return request.tenant_id
    parsed = urllib.parse.urlparse(request.credential_lookup_url)
    parts = [part for part in parsed.path.split("/") if part]
    return parts[-1] if parts else ""


def _session_state_path(tenant_id: str, email: str) -> Path:
    settings.session_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(f"{tenant_id}:{email.lower()}".encode("utf-8")).hexdigest()[:32]
    return settings.session_dir / f"stuvia-{digest}.json"


def _clear_session_state(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


async def _stored_session_active(page: Page) -> bool:
    response = await page.goto(settings.stuvia_upload_url, wait_until="domcontentloaded", timeout=settings.navigation_timeout_ms)
    if response and response.status == 403:
        screenshot = await _capture_debug_screenshot(page, "stuvia-cloudfront-session-block")
        raise RuntimeError(
            "Stuvia/CloudFront returned HTTP 403 while checking the stored session. "
            f"Screenshot: {screenshot}"
        )
    await _assert_stuvia_page_available(page, "stuvia-cloudfront-session-block")
    try:
        await page.wait_for_load_state("networkidle", timeout=5000)
    except PlaywrightTimeoutError:
        pass
    await _dismiss_popups(page)
    body_text = (await page.locator("body").inner_text(timeout=5000)).lower()
    if "/login" in page.url:
        return False
    if "log in or sign up" in body_text and "continue with email" in body_text:
        return False
    return True


async def _authenticated_browser_context(playwright: Any, tenant_id: str, email: str, password: str) -> tuple[Any, Any, Page, bool]:
    session_path = _session_state_path(tenant_id, email)
    if session_path.exists():
        browser, context = await _new_browser_context(playwright, session_path)
        page = await context.new_page()
        if await _stored_session_active(page):
            return browser, context, page, True
        await context.close()
        await browser.close()
        _clear_session_state(session_path)

    browser, context = await _new_browser_context(playwright)
    page = await context.new_page()
    try:
        await _login(page, email, password)
        await context.storage_state(path=str(session_path))
    except Exception:
        _clear_session_state(session_path)
        raise
    return browser, context, page, False


def _document_package_url(document_id: str, tenant_id: str) -> str:
    query = urllib.parse.urlencode({"tenant_id": tenant_id})
    return f"{settings.backend_base_url}/api/v1/stuvia-agent/publisher/documents/{document_id}?{query}"


def _post_results(run_id: str | None, results: list[dict[str, Any]]) -> None:
    _json_request(
        f"{settings.backend_base_url}/api/v1/stuvia-agent/publisher/results",
        method="POST",
        payload={"run_id": run_id, "results": results},
        timeout=30,
    )


async def _post_results_safe(run_id: str | None, results: list[dict[str, Any]]) -> None:
    if not run_id or not results:
        return
    try:
        await asyncio.to_thread(_post_results, run_id, results)
    except Exception as exc:
        print(f"Failed to post Stuvia publisher results for run {run_id}: {exc}", flush=True)


def _failure_results(listings: list[PublishListing], error: str) -> list[dict[str, Any]]:
    return [
        {
            "document_id": listing.document_id,
            "status": "failed",
            "listing": {},
            "error": error,
        }
        for listing in listings
        if listing.document_id
    ]


def _publisher_response(request: PublishRequest, results: list[dict[str, Any]]) -> dict[str, Any]:
    success_count = sum(1 for item in results if item.get("status") in {"published", "submitted_for_review", "dry_run_ready"})
    return {
        "ok": bool(results) and success_count > 0 and success_count == len(results),
        "run_id": request.run_id,
        "dry_run": settings.dry_run,
        "published": success_count,
        "failed": len(results) - success_count,
        "results": results,
    }


def _return_or_raise_publisher_response(request: PublishRequest, results: list[dict[str, Any]]) -> dict[str, Any]:
    response = _publisher_response(request, results)
    if response["ok"]:
        return response
    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=response)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "StudyMint Stuvia Publisher"}


async def _execute_publish_request(request: PublishRequest, *, post_callback: bool = True) -> list[dict[str, Any]]:
    publish_listings = [listing for listing in request.listings if listing.document_id]
    if not publish_listings:
        return []

    tenant_id = _tenant_id_from_request(request)
    if not tenant_id:
        results = _failure_results(publish_listings, "tenant_id or credential_lookup_url is required")
        if post_callback:
            await _post_results_safe(request.run_id, results)
        return results
    if not request.credential_lookup_url:
        results = _failure_results(publish_listings, "credential_lookup_url is required")
        if post_callback:
            await _post_results_safe(request.run_id, results)
        return results

    try:
        credentials = _json_request(request.credential_lookup_url, timeout=30)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        results = _failure_results(publish_listings, f"Unable to fetch Stuvia credentials: {detail}")
        if post_callback:
            await _post_results_safe(request.run_id, results)
        return results
    except Exception as exc:
        results = _failure_results(publish_listings, f"Unable to fetch Stuvia credentials: {exc}")
        if post_callback:
            await _post_results_safe(request.run_id, results)
        return results

    email = credentials.get("stuvia_email")
    password = credentials.get("stuvia_password")
    if not email or not password:
        results = _failure_results(publish_listings, "Stuvia credentials are not configured")
        if post_callback:
            await _post_results_safe(request.run_id, results)
        return results

    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="stuvia-publish-") as tmp_dir:
        async with async_playwright() as playwright:
            try:
                browser, context, page, session_reused = await _authenticated_browser_context(playwright, tenant_id, email, password)
            except Exception as exc:
                results = [
                    {
                        "document_id": listing.document_id,
                        "status": "failed",
                        "listing": {},
                        "error": str(exc),
                    }
                    for listing in publish_listings
                ]
                browser = None
                context = None
                page = None
                session_reused = False

            try:
                if page is not None and context is not None:
                    for listing in publish_listings:
                        if any(result.get("document_id") == listing.document_id for result in results):
                            continue
                        result: dict[str, Any] = {"document_id": listing.document_id, "status": "failed", "listing": {}}
                        try:
                            document = _json_request(_document_package_url(listing.document_id, tenant_id), timeout=60)
                            metadata = _listing_metadata(document, listing)
                            pdf_path = Path(tmp_dir) / f"{listing.document_id}.pdf"
                            _download_file(document["pdf_url"], pdf_path)
                            publish_result = await asyncio.wait_for(
                                _publish_in_browser(page, pdf_path, metadata),
                                timeout=settings.listing_timeout_seconds,
                            )
                            result.update(publish_result)
                            result["listing"] = metadata
                            result["session_reused"] = session_reused
                        except asyncio.TimeoutError:
                            screenshot = await _capture_debug_screenshot(page, "stuvia-publish-timeout")
                            result["error"] = (
                                f"Stuvia publishing timed out after {settings.listing_timeout_seconds} seconds. "
                                f"Screenshot: {screenshot}"
                            )
                        except Exception as exc:
                            result["error"] = str(exc)
                        results.append(result)
                    try:
                        session_path = _session_state_path(tenant_id, email)
                        await context.storage_state(path=str(session_path))
                    except Exception:
                        pass
            finally:
                if context is not None:
                    await context.close()
                if browser is not None:
                    await browser.close()

    if post_callback:
        await _post_results_safe(request.run_id, results)

    return results


async def _publish_background(request: PublishRequest) -> None:
    try:
        await _execute_publish_request(request, post_callback=True)
    except Exception as exc:
        publish_listings = [listing for listing in request.listings if listing.document_id]
        await _post_results_safe(request.run_id, _failure_results(publish_listings, f"Publisher crashed: {exc}"))


@app.post("/publish/async")
async def publish_async(request: PublishRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_token(authorization)
    publish_listings = [listing for listing in request.listings if listing.document_id]
    if not publish_listings:
        return _publisher_response(request, [])

    asyncio.create_task(_publish_background(request))
    return {
        "ok": True,
        "run_id": request.run_id,
        "dry_run": settings.dry_run,
        "status": "queued",
        "queued": len(publish_listings),
        "message": "Stuvia publishing queued in the browser publisher.",
    }


@app.post("/publish")
async def publish(request: PublishRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_token(authorization)
    results = await _execute_publish_request(request, post_callback=True)

    return _return_or_raise_publisher_response(request, results)
