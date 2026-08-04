from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class SourceCitation:
    source_id: str
    title: str
    locator: str
    excerpt: str
    jurisdiction: str | None = None
    effective_date: str | None = None


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def citation_from_document(document: Any, index: int) -> SourceCitation:
    metadata = dict(getattr(document, "metadata", {}) or {})
    content = _clean(getattr(document, "page_content", ""))
    title = _clean(
        metadata.get("title")
        or metadata.get("file_name")
        or metadata.get("filename")
        or metadata.get("source")
        or f"Retrieved source {index}"
    )
    locator = _clean(
        metadata.get("pinpoint")
        or metadata.get("page")
        or metadata.get("section")
        or metadata.get("source")
        or "locator unavailable"
    )
    source_id = _clean(metadata.get("source_id") or f"SRC-{index:03d}")
    jurisdiction = _clean(metadata.get("jurisdiction")) or None
    effective_date = _clean(metadata.get("effective_date")) or None
    return SourceCitation(
        source_id=source_id,
        title=title,
        locator=locator,
        excerpt=content[:500],
        jurisdiction=jurisdiction,
        effective_date=effective_date,
    )


def build_source_report(documents: Iterable[Any]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    report: list[dict[str, Any]] = []
    for index, document in enumerate(documents, start=1):
        citation = citation_from_document(document, index)
        identity = (citation.source_id, citation.title, citation.locator)
        if identity in seen:
            continue
        seen.add(identity)
        report.append(asdict(citation))
    return report


def grounding_status(source_report: list[dict[str, Any]]) -> dict[str, Any]:
    if not source_report:
        return {
            "status": "NO_RETRIEVED_SUPPORT",
            "filing_safe": False,
            "warnings": [
                "No source was returned by retrieval.",
                "Do not treat the answer as supported legal research.",
            ],
        }

    missing_locators = [
        source["source_id"]
        for source in source_report
        if source.get("locator") == "locator unavailable"
    ]
    missing_jurisdiction = [
        source["source_id"]
        for source in source_report
        if not source.get("jurisdiction")
    ]
    missing_effective_date = [
        source["source_id"]
        for source in source_report
        if not source.get("effective_date")
    ]

    warnings = [
        "Retrieved material has not been independently validated as current controlling authority.",
        "Answer text is internal research assistance, not legal advice or filing-ready work product.",
    ]
    if missing_locators:
        warnings.append(f"Missing pinpoint locators: {', '.join(missing_locators)}")
    if missing_jurisdiction:
        warnings.append(f"Missing jurisdiction metadata: {', '.join(missing_jurisdiction)}")
    if missing_effective_date:
        warnings.append(f"Missing effective-date metadata: {', '.join(missing_effective_date)}")

    return {
        "status": "RETRIEVED_SOURCES_PRESENT",
        "filing_safe": False,
        "source_count": len(source_report),
        "missing_locators": missing_locators,
        "missing_jurisdiction": missing_jurisdiction,
        "missing_effective_date": missing_effective_date,
        "warnings": warnings,
    }
