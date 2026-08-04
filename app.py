from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from lawglance_main import Lawglance, NO_SUPPORT_ANSWER


LOGGER = logging.getLogger("lawglance")
APP_ROOT = Path(__file__).resolve().parent


def render_sources_and_grounding(message: dict) -> None:
    sources = list(message.get("sources") or [])
    grounding = dict(message.get("grounding") or {})
    with st.expander(f"Retrieved sources ({len(sources)})"):
        if not sources:
            st.write("No sources were returned by retrieval.")
        for source in sources:
            st.markdown(
                f"**{source.get('source_id', 'UNKNOWN')} — {source.get('title', 'Untitled')}**  \n"
                f"Locator: `{source.get('locator') or 'not supplied'}`  \n"
                f"Jurisdiction: `{source.get('jurisdiction') or 'not supplied'}`  \n"
                f"Effective date: `{source.get('effective_date') or 'not supplied'}`"
            )
            if source.get("source_id_generated"):
                st.caption("Source identifier generated from retrieved metadata/content; replace with a stable authority ID.")
            if source.get("excerpt"):
                st.code(source["excerpt"], language=None)
    st.caption(f"Grounding status: {grounding.get('status', 'UNKNOWN')}")
    for warning in grounding.get("warnings", []):
        st.warning(warning)


@st.cache_resource(show_spinner=False)
def load_shared_resources(api_key: str, chroma_directory: str):
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        openai_api_key=api_key,
    )
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    vector_store = Chroma(
        persist_directory=chroma_directory,
        embedding_function=embeddings,
    )
    return llm, embeddings, vector_store


st.set_page_config(page_title="LawGlance", page_icon="⚖️", layout="wide")
st.title("LawGlance — Source-Grounded Legal Research")
st.caption("Internal research assistance. Not legal advice or filing-ready work product.")

with st.sidebar:
    st.header("Operating boundary")
    st.markdown(
        """
        - Answers are generated only from retrieved context.
        - Retrieved material is not automatically current or controlling.
        - Source metadata may be incomplete.
        - Verify every proposition against primary authority before use.
        - No deadline, misconduct finding, or legal conclusion is certified here.
        """
    )

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("OPENAI_API_KEY is not configured. The application cannot run.")
    st.stop()

configured_chroma = os.getenv("LAWGLANCE_CHROMA_DIR")
chroma_path = Path(configured_chroma).expanduser() if configured_chroma else APP_ROOT / "chroma_db_legal_bot_part1"
chroma_path = chroma_path.resolve()
if not chroma_path.is_dir():
    st.error(
        "The reviewed Chroma index directory does not exist. Set LAWGLANCE_CHROMA_DIR "
        "to an existing absolute directory or place the reviewed index beside the app."
    )
    st.stop()

llm, embeddings, vector_store = load_shared_resources(openai_api_key, str(chroma_path))
if "lawglance" not in st.session_state:
    st.session_state.lawglance = Lawglance(llm, embeddings, vector_store, max_sessions=1)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

law: Lawglance = st.session_state.lawglance

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources_and_grounding(message)

prompt = st.chat_input("Ask a legal research question")
if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        result = law.conversational(prompt, session_id=st.session_state.session_id)
    except Exception:
        LOGGER.exception("LawGlance request failed")
        st.error("The research request failed. No answer or chat-history entry was saved.")
        st.stop()

    user_message = {"role": "user", "content": prompt}
    assistant_message = {
        "role": "assistant",
        "content": result.get("answer") or NO_SUPPORT_ANSWER,
        "sources": list(result.get("sources") or []),
        "grounding": dict(result.get("grounding") or {}),
    }
    st.session_state.messages.extend([user_message, assistant_message])

    with st.chat_message("assistant"):
        st.markdown(assistant_message["content"])
        render_sources_and_grounding(assistant_message)
