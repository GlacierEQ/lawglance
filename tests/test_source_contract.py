import unittest

from source_contract import build_source_report, citation_from_document, grounding_status


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
        self.assertEqual(citation.locator, "Rule 4(a)(1)")
        self.assertEqual(citation.jurisdiction, "Hawaii")

    def test_source_report_deduplicates_exact_metadata_identity(self):
        document = Document(
            "Same content.",
            {"source_id": "SRC-1", "title": "Order", "page": "2"},
        )
        report = build_source_report([document, document])
        self.assertEqual(len(report), 1)

    def test_no_sources_blocks_support(self):
        status = grounding_status([])
        self.assertEqual(status["status"], "NO_RETRIEVED_SUPPORT")
        self.assertFalse(status["filing_safe"])

    def test_missing_metadata_is_exposed(self):
        report = build_source_report([Document("Text without metadata.")])
        status = grounding_status(report)
        self.assertEqual(status["status"], "RETRIEVED_SOURCES_PRESENT")
        self.assertFalse(status["filing_safe"])
        self.assertEqual(status["missing_locators"], ["SRC-001"])
        self.assertEqual(status["missing_jurisdiction"], ["SRC-001"])
        self.assertEqual(status["missing_effective_date"], ["SRC-001"])

    def test_excerpt_is_bounded(self):
        report = build_source_report([Document("x" * 1000, {"source_id": "S", "title": "T"})])
        self.assertEqual(len(report[0]["excerpt"]), 500)


if __name__ == "__main__":
    unittest.main()
