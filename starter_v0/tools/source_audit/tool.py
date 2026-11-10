from __future__ import annotations

from typing import Any
from urllib.parse import urlparse, urlunparse


def _normalized_url(value: str) -> str | None:
    parsed = urlparse(value.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=parsed.path.rstrip("/") or "/",
        fragment="",
    )
    return urlunparse(normalized)


def audit_sources(items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if not isinstance(items, list):
        return {"tool": "source_audit", "error": "ValueError", "message": "items must be a list"}

    audited: list[dict[str, Any]] = []
    seen_urls: dict[str, int] = {}
    for index, item in enumerate(items):
        issues: list[str] = []
        duplicate_of: int | None = None
        if not isinstance(item, dict):
            issues.append("invalid_item")
            audited.append({"index": index, "issues": issues, "duplicate_of": duplicate_of})
            continue

        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            issues.append("missing_title")

        url = item.get("url")
        if not isinstance(url, str) or not url.strip():
            issues.append("missing_url")
        else:
            normalized_url = _normalized_url(url)
            if normalized_url is None:
                issues.append("invalid_url")
            elif normalized_url in seen_urls:
                issues.append("duplicate_url")
                duplicate_of = seen_urls[normalized_url]
            else:
                seen_urls[normalized_url] = index

        audited.append({"index": index, "issues": issues, "duplicate_of": duplicate_of})

    issue_count = sum(len(item["issues"]) for item in audited)
    return {
        "tool": "source_audit",
        "item_count": len(items),
        "issue_count": issue_count,
        "is_clean": issue_count == 0,
        "items": audited,
    }
