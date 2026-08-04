import unittest

from source_contract import (
    NO_SUPPORT_ANSWER,
    build_source_report,
    citation_from_document,
    enforce_grounded_answer,
    grounding_status,
)


class Document:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


class SourceContractTests(unittest.TestCase):
    def test_citation_uses_source_metadata(self):
        document = Document(
            "Rule text and explanation.",
            {
                "source_id": "AUTH-001",
                "title": "Official Rule",
                "pinpoint": "Rule 4(a)(1)",
                "jurisdiction": "Hawaii",
                "effective_date": "2025-07-01",
            },
        )
        citation = citation_from_document(document, 1)
        self.assertEqual(citation.source_id, "AUTH-001")
        self.assertFalse(citation.source_id_generated)
        self.assertEqual(citation.locator, "Rule 4(a)(1)")
        self.assertEqual(citation.jurisdiction, "Hawaii")

    def test_source_report_deduplicates_exact_metadata_identity(self):
        document = Document(
            "Same content.",
            {"source_id": "SRC-1", "title": "Order", "page": "2"},
        )
        report = build_source_report([document, document])
        self.assertEqual(len(report), 1)

    def test_generated_id_is_stable_across_retrieval_order(self):
        first = Document("Same content.", {"title": "Order", "page": "2"})
        other = Document("Other content.", {"title": "Other", "page": "1"})
        report_a = build_source_report([first, other])
        report_b = build_source_report([other, first])
        first_id_a = next(item["source_id"] for item in report_a if item["title"] == "Order")
        first_id_b = next(item["source_id"] for item in report_b if item["title"] == "Order")
        self.assertEqual(first_id_a, first_id_b)
        self.assertTrue(first_id_a.startswith("GEN-"))

    def test_authority_versions_are_not_collapsed(self):
        older = Document(
            "Rule text.",
            {
                "source_id": "RULE-4",
                "title": "Rule 4",
                "pinpoint": "4(a)",
                "jurisdiction": "Hawaii",
                "effective_date": "2025-07-01",
            },
        )
        newer = Document(
            "Rule text.",
            {
                "source_id": "RULE-4",
                "title": "Rule 4",
                "pinpoint": "4(a)",
                "jurisdiction": "Hawaii",
                "effective_date": "2027-01-01",
            },
        )
        self.assertEqual(len(build_source_report([older, newer])), 2)

    def test_whitespace_metadata_uses_missing_fallbacks(self):
        report = build_source_report(
            [Document("Text.", {"source_id": "   ", "pinpoint": "   "})]
        )
        self.assertTrue(report[0]["source_id_generated"])
        self.assertEqual(report[0]["locator"], "locator unavailable")

    def test_no_sources_blocks_support(self):
        status = grounding_status([])
        self.assertEqual(status["status"], "NO_RETRIEVED_SUPPORT")
        self.assertFalse(status["filing_safe"])

    def test_no_sources_override_model_text(self):
        self.assertEqual(
            enforce_grounded_answer("Unsupported model text", []),
            NO_SUPPORT_ANSWER,
        )

    def test_sources_preserve_nonempty_model_text(self):
        sources = build_source_report(
            [Document("Text.", {"source_id": "S", "title": "T"})]
        )
        self.assertEqual(enforce_grounded_answer("Supported answer", sources), "Supported answer")

    def test_missing_metadata_is_exposed(self):
        report = build_source_report([Document("Text without metadata.")])
        source_id = report[0]["source_id"]
        status = grounding_status(report)
        self.assertEqual(status["status"], "RETRIEVED_SOURCES_PRESENT")
        self.assertFalse(status["filing_safe"])
        self.assertEqual(status["missing_locators"], [source_id])
        self.assertEqual(status["missing_jurisdiction"], [source_id])
        self.assertEqual(status["missing_effective_date"], [source_id])
        self.assertEqual(status["generated_source_ids"], [source_id])

    def test_excerpt_is_bounded(self):
        report = build_source_report(
            [Document("x" * 1000, {"source_id": "S", "title": "T"})]
        )
        self.assertEqual(len(report[0]["excerpt"]), 500)


if __name__ == "__main__":
    unittest.main()
