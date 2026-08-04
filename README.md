# LawGlance

Source-grounded conversational retrieval for internal legal research.

## Status

- Application type: Streamlit legal RAG pilot
- Answer model: OpenAI through LangChain
- Retrieval: local Chroma vector store
- Filing-ready output: no
- Current-authority validation: not implemented
- External legal action: not implemented

## Hardening applied

This branch changes the application from answer-only output to a structured response containing:

- answer text;
- retrieved source descriptors;
- pinpoint locator where supplied;
- jurisdiction metadata where supplied;
- effective-date metadata where supplied;
- source excerpts;
- grounding status;
- explicit missing-metadata warnings.

The generation temperature is reduced from `0.9` to `0.1`. The prompt prohibits invented cases, quotations, holdings, dates, jurisdictions, citations, deadlines, elements, and procedural postures. When retrieval provides no support, the required answer is:

> The retrieved sources do not support an answer.

## Architecture

```text
user question
  -> history-aware standalone question
  -> Chroma retrieval
  -> bounded context-only answer
  -> source report
  -> grounding and metadata warnings
  -> human legal review
```

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=...
streamlit run app.py
```

The local vector store must exist at `chroma_db_legal_bot_part1` or the application must be configured for another reviewed source index.

## Tests

The source contract has dependency-light unit tests:

```bash
python -m unittest tests.test_source_contract
```

Syntax validation:

```bash
python -m py_compile app.py lawglance_main.py source_contract.py tests/test_source_contract.py
```

## Source metadata contract

For useful source display, indexed documents should carry:

```json
{
  "source_id": "stable source identifier",
  "title": "document or authority title",
  "pinpoint": "page, paragraph, section, or docket locator",
  "jurisdiction": "authority jurisdiction",
  "effective_date": "effective or checked-through date",
  "source": "controlled URI or internal locator"
}
```

Missing metadata is exposed rather than inferred.

## Legal boundary

Retrieval does not establish that a source is authentic, current, controlling, precedential, admissible, or relevant to a particular matter. A citation candidate is not proposition support. A summary is derivative work product. Every external legal use requires primary-source review, current authority, contrary-authority analysis, and human approval.

The application must not be used to manufacture accusations of fraud, bias, corruption, conspiracy, fabrication, retaliation, obstruction, criminal conduct, or civil-rights violations.

## Data boundary

Do not ingest credentials, sealed records, privileged-review notes, private addresses, medical or school records, or protected child information into an unapproved vector store. Preserve native records separately and use controlled identifiers in retrieval metadata.

## Known unresolved work

- dependency versions require compatibility reconciliation;
- authority freshness and subsequent-history checking are not implemented;
- source authentication and hashing are not implemented;
- retrieval evaluation and jurisdiction-specific benchmark sets are not implemented;
- case-specific deployment is not established.
