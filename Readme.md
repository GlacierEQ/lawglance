# LawGlance — Source-Grounded Legal Research

LawGlance is a Streamlit retrieval-augmented research pilot for the Indian legal materials represented in its reviewed Chroma index. The present repository does not establish coverage of Hawai'i law, United States law, current controlling authority, or any specific case.

## Status

- Application type: Streamlit legal RAG pilot
- Jurisdictional scope: Indian-law materials described by the project and actually present in the configured index
- Answer model: OpenAI through LangChain
- Retrieval: existing local Chroma vector store
- Filing-ready output: no
- Current-authority and subsequent-history validation: not implemented
- External legal action: not implemented

## Source-grounding controls

The hardened response contract contains:

- answer text;
- retrieved source descriptors;
- deterministic source identifiers where an index did not supply one;
- pinpoint locator where supplied;
- jurisdiction metadata where supplied;
- effective-date metadata where supplied;
- bounded source excerpts;
- grounding status;
- explicit missing-metadata warnings.

Generation temperature is `0.1`. Application code—not merely the prompt—forces the following result whenever retrieval returns no source:

> The retrieved sources do not support an answer.

Sessions are browser-session scoped, require an explicit generated session identifier, and use a bounded in-memory history store. A failed request is not committed to visible conversation history.

## Architecture

```text
user question
  -> browser-session history
  -> standalone research question
  -> reviewed Chroma directory
  -> source retrieval
  -> bounded context-only answer
  -> deterministic source report
  -> grounding and metadata warnings
  -> human legal review
```

## Legal coverage represented by the original project

The upstream project describes support for:

- Constitution of India;
- Bharatiya Nyaya Sanhita, 2023;
- Bharatiya Nagarik Suraksha Sanhita, 2023;
- Bharatiya Sakshya Adhiniyam, 2023;
- Consumer Protection Act, 2019;
- Motor Vehicles Act, 1988;
- Information Technology Act, 2000.

That description does not prove that every authority is present, current, complete, or correctly indexed. The configured vector store controls what the application can retrieve.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=...
export LAWGLANCE_CHROMA_DIR=/absolute/path/to/reviewed/chroma_db
streamlit run app.py
```

The application refuses to start when the configured Chroma directory does not exist, preventing silent creation or use of an empty index from the wrong working directory.

## Dependency generation

The chain implementation uses the current separated package generation:

- `langchain-classic` for legacy retrieval-chain APIs;
- `langchain-community` for community integrations;
- `langchain-openai` for OpenAI models and embeddings;
- `langchain-chroma` for Chroma integration.

Versions are pinned together in `requirements.txt` and checked by CI installation and import smoke tests.

## Tests

```bash
python -m unittest tests.test_source_contract
python -m py_compile app.py lawglance_main.py source_contract.py tests/test_source_contract.py
```

Tests cover deterministic source identity, authority-version separation, whitespace metadata, exact deduplication, bounded excerpts, missing metadata, and deterministic no-support refusal.

## Source metadata contract

Indexed documents should carry:

```json
{
  "source_id": "stable repository or authority identifier",
  "title": "document or authority title",
  "pinpoint": "page, paragraph, section, or docket locator",
  "jurisdiction": "authority jurisdiction",
  "effective_date": "effective or checked-through date",
  "source": "controlled URI or internal locator"
}
```

Missing metadata is exposed rather than inferred. Generated source identifiers are explicitly flagged and must be replaced by stable identifiers before higher-trust use.

## Legal boundary

Retrieval does not establish that a source is authentic, current, controlling, precedential, admissible, or relevant to a particular matter. A citation candidate is not proposition support. A summary is derivative work product. Every external legal use requires primary-source review, current-authority review, contrary-authority analysis, jurisdiction confirmation, and human approval.

The application must not be used to manufacture allegations of fraud, bias, corruption, conspiracy, fabrication, retaliation, obstruction, criminal conduct, or civil-rights violations.

## Data boundary

Do not ingest credentials, sealed records, privileged-review notes, private addresses, medical or school records, or protected child information into an unapproved vector store. Preserve native records separately and use controlled identifiers in retrieval metadata.

## Unresolved work

- source authentication and byte hashing are not implemented;
- authority freshness and subsequent-history checking are not implemented;
- retrieval quality has not been benchmarked by jurisdiction or proposition type;
- a case-specific deployment has not been established;
- full runtime tests require a reviewed Chroma index and an authorized model credential.

## License

The repository retains its existing upstream license and attribution history. Confirm the controlling license file and upstream obligations before redistribution or deployment.
