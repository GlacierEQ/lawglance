from __future__ import annotations

import os
import uuid

import streamlit as st
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from lawglance_main import Lawglance


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

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    openai_api_key=openai_api_key,
)
embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
vector_store = Chroma(
    persist_directory="chroma_db_legal_bot_part1",
    embedding_function=embeddings,
)
law = Lawglance(llm, embeddings, vector_store)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander(f"Retrieved sources ({len(message['sources'])})"):
                for source in message["sources"]:
                    st.markdown(
                        f"**{source['source_id']} — {source['title']}**  \n"
                        f"Locator: `{source['locator']}`  \n"
                        f"Jurisdiction: `{source.get('jurisdiction') or 'not supplied'}`  \n"
                        f"Effective date: `{source.get('effective_date') or 'not supplied'}`"
                    )
                    if source.get("excerpt"):
                        st.code(source["excerpt"], language=None)
        if message.get("grounding"):
            grounding = message["grounding"]
            st.caption(f"Grounding status: {grounding['status']}")
            for warning in grounding.get("warnings", []):
                st.warning(warning)

prompt = st.chat_input("Ask a legal research question")
if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        result = law.conversational(prompt, session_id=st.session_state.session_id)
    except Exception as exc:
        st.exception(exc)
        st.stop()

    with st.chat_message("assistant"):
        st.markdown(result["answer"] or "The retrieved sources do not support an answer.")
        with st.expander(f"Retrieved sources ({len(result['sources'])})"):
            if not result["sources"]:
                st.write("No sources were returned by retrieval.")
            for source in result["sources"]:
                st.markdown(
                    f"**{source['source_id']} — {source['title']}**  \n"
                    f"Locator: `{source['locator']}`  \n"
                    f"Jurisdiction: `{source.get('jurisdiction') or 'not supplied'}`  \n"
                    f"Effective date: `{source.get('effective_date') or 'not supplied'}`"
                )
                if source.get("excerpt"):
                    st.code(source["excerpt"], language=None)
        st.caption(f"Grounding status: {result['grounding']['status']}")
        for warning in result["grounding"].get("warnings", []):
            st.warning(warning)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"] or "The retrieved sources do not support an answer.",
            "sources": result["sources"],
            "grounding": result["grounding"],
        }
    )
