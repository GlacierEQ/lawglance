from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any, Iterable


NO_SUPPORT_ANSWER = "The retrieved sources do not support an answer."


@dataclass(frozen=True)
class SourceCitation:
    source_id: str
    source_id_generated: bool
    title: str
    locator: str
    excerpt: str
    jurisdiction: str | None = None
    effective_date: str | None = None


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _first_clean(*values: Any) -> str:
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return ""


def _generated_source_id(
    *,
    title: str,
    locator: str,
    jurisdiction: str | None,
    effective_date: str | None,
    content: str,
) -> str:
    payload = "\x1f".join(
        [title, locator, jurisdiction or "", effective_date or "", content]
    ).encode("utf-8")
    return f"GEN-{hashlib.sha256(payload).hexdigest()[:20].upper()}"


def citation_from_document(document: Any, index: int) -> SourceCitation:
    metadata = dict(getattr(document, "metadata", {}) or {})
    content = _clean(getattr(document, "page_content", ""))
    title = _first_clean(
        metadata.get("title"),
        metadata.get("file_name"),
        metadata.get("filename"),
        metadata.get("source"),
    ) or f"Retrieved source {index}"
    locator = _first_clean(
        metadata.get("pinpoint"),
        metadata.get("page"),
        metadata.get("section"),
        metadata.get("source"),
    ) or "locator unavailable"
    jurisdiction = _first_clean(metadata.get("jurisdiction")) or None
    effective_date = _first_clean(metadata.get("effective_date")) or None
    supplied_source_id = _first_clean(metadata.get("source_id"))
    source_id_generated = not bool(supplied_source_id)
    source_id = supplied_source_id or _generated_source_id(
        title=title,
        locator=locator,
        jurisdiction=jurisdiction,
        effective_date=effective_date,
        content=content,
    )
    return SourceCitation(
        source_id=source_id,
        source_id_generated=source_id_generated,
        title=title,
        locator=locator,
        excerpt=content[:500],
        jurisdiction=jurisdiction,
        effective_date=effective_date,
    )


def build_source_report(documents: Iterable[Any]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str | None, str | None]] = set()
    report: list[dict[str, Any]] = []
    for index, document in enumerate(documents, start=1):
        citation = citation_from_document(document, index)
        identity = (
            citation.source_id,
            citation.title,
            citation.locator,
            citation.jurisdiction,
            citation.effective_date,
        )
        if identity in seen:
            continue
        seen.add(identity)
        report.append(asdict(citation))
    return report


def enforce_grounded_answer(answer: Any, source_report: list[dict[str, Any]]) -> str:
    if not source_report:
        return NO_SUPPORT_ANSWER
    cleaned = _clean(answer)
    return cleaned or NO_SUPPORT_ANSWER


def _missing(value: Any, *, sentinel: str | None = None) -> bool:
    cleaned = _clean(value)
    return not cleaned or (sentinel is not None and cleaned == sentinel)


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
        if _missing(source.get("locator"), sentinel="locator unavailable")
    ]
    missing_jurisdiction = [
        source["source_id"]
        for source in source_report
        if _missing(source.get("jurisdiction"))
    ]
    missing_effective_date = [
        source["source_id"]
        for source in source_report
        if _missing(source.get("effective_date"))
    ]
    generated_source_ids = [
        source["source_id"]
        for source in source_report
        if source.get("source_id_generated")
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
    if generated_source_ids:
        warnings.append(
            "Generated source identifiers require replacement by stable repository or authority identifiers: "
            + ", ".join(generated_source_ids)
        )

    return {
        "status": "RETRIEVED_SOURCES_PRESENT",
        "filing_safe": False,
        "source_count": len(source_report),
        "missing_locators": missing_locators,
        "missing_jurisdiction": missing_jurisdiction,
        "missing_effective_date": missing_effective_date,
        "generated_source_ids": generated_source_ids,
        "warnings": warnings,
    }
