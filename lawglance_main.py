from __future__ import annotations

from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from source_contract import build_source_report, grounding_status


class Lawglance:
    """Conversational legal-research RAG with explicit source-return boundaries.

    The class retrieves context, generates a bounded answer, and returns both the
    answer and a structured source report. It does not determine current
    controlling authority or produce filing-ready legal work.
    """

    store: dict[str, ChatMessageHistory] = {}

    def __init__(self, llm, embeddings, vector_store):
        self.llm = llm
        self.embeddings = embeddings
        self.vector_store = vector_store

    def _retriever(self):
        return self.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 8, "score_threshold": 0.45},
        )

    def llm_answer_generator(self):
        retriever = self._retriever()
        contextualize_q_system_prompt = (
            "Given the chat history and latest question, produce one standalone "
            "research question. Do not answer it and do not add facts."
        )
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        history_aware_retriever = create_history_aware_retriever(
            self.llm,
            retriever,
            contextualize_q_prompt,
        )

        system_prompt = (
            "You are a legal research assistant, not a lawyer and not a court. "
            "Answer only from the supplied context. Distinguish what the context "
            "states from inference. Do not invent a case, quotation, holding, date, "
            "jurisdiction, citation, deadline, element, or procedural posture. If the "
            "context does not support an answer, say exactly: 'The retrieved sources "
            "do not support an answer.' Do not characterize conduct as fraud, bias, "
            "corruption, conspiracy, fabrication, retaliation, obstruction, or a civil-"
            "rights violation unless the supplied context itself establishes every "
            "necessary proposition. Treat the answer as internal research assistance."
        )
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                (
                    "human",
                    "Question:\n{input}\n\nRetrieved context:\n{context}\n\n"
                    "Provide a concise source-bounded answer. Identify uncertainty "
                    "and contrary material contained in the context. Do not claim "
                    "that the answer is filing-ready or current controlling law.",
                ),
            ]
        )

        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)
        return create_retrieval_chain(history_aware_retriever, question_answer_chain)

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in Lawglance.store:
            Lawglance.store[session_id] = ChatMessageHistory()
        return Lawglance.store[session_id]

    def conversational(self, query: str, session_id: str = "default") -> dict:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")

        rag_chain = self.llm_answer_generator()
        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
        response = conversational_rag_chain.invoke(
            {"input": query.strip()},
            config={"configurable": {"session_id": session_id.strip()}},
        )

        sources = build_source_report(response.get("context", []))
        return {
            "answer": str(response.get("answer", "")).strip(),
            "sources": sources,
            "grounding": grounding_status(sources),
            "query": query.strip(),
            "session_id": session_id.strip(),
        }
