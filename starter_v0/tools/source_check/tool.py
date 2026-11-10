from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

from tools._shared import err


def _canonical_url(value: str) -> str | None:
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        host = parsed.hostname.lower()
        if parsed.port:
            host = f"{host}:{parsed.port}"
        path = parsed.path.rstrip("/") or "/"
        return urlunsplit((parsed.scheme.lower(), host, path, parsed.query, ""))
    except (TypeError, ValueError):
        return None


def check_sources(items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Check citation metadata and URL syntax without making network requests."""
    if items is None:
        items = []
    if not isinstance(items, list):
        return err("source_check", ValueError("items must be a list of source objects"))

    checked: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    valid_count = 0

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            return err("source_check", ValueError(f"items[{index}] must be an object"))

        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        issues: list[str] = []
        if not title:
            issues.append("missing_title")
        if not url:
            issues.append("missing_url")
            canonical = None
        else:
            canonical = _canonical_url(url)
            if canonical is None:
                issues.append("invalid_url")
            elif canonical in seen_urls:
                issues.append("duplicate_url")
            else:
                seen_urls.add(canonical)

        source = str(item.get("source") or "").strip()
        if not source and canonical:
            source = urlsplit(canonical).hostname or ""

        result_item = dict(item)
        result_item.update({
            "title": title,
            "url": url,
            "source": source,
            "issues": issues,
            "status": "valid" if not issues else "needs_review",
        })
        checked.append(result_item)
        if not issues:
            valid_count += 1

    return {
        "tool": "source_check",
        "checked_count": len(checked),
        "valid_count": valid_count,
        "items": checked,
        "scope_note": "Checks citation fields and URL syntax only; it does not verify page availability or factual accuracy.",
    }
