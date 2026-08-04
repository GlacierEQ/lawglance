from __future__ import annotations

from collections import OrderedDict

from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from source_contract import build_source_report, grounding_status


NO_SUPPORT_ANSWER = "The retrieved sources do not support an answer."


class Lawglance:
    """Conversational legal-research RAG with explicit source-return boundaries."""

    def __init__(self, llm, embeddings, vector_store, *, max_sessions: int = 1):
        if max_sessions < 1:
            raise ValueError("max_sessions must be at least 1")
        self.llm = llm
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.max_sessions = max_sessions
        self.store: OrderedDict[str, ChatMessageHistory] = OrderedDict()

    def _retriever(self):
        return self.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 8, "score_threshold": 0.45},
        )

    def llm_answer_generator(self):
        retriever = self._retriever()
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Given the chat history and latest question, produce one standalone "
                    "research question. Do not answer it and do not add facts.",
                ),
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
            f"context does not support an answer, say exactly: '{NO_SUPPORT_ANSWER}' "
            "Do not characterize conduct as fraud, bias, corruption, conspiracy, "
            "fabrication, retaliation, obstruction, criminal conduct, or a civil-rights "
            "violation unless the supplied context establishes every necessary proposition. "
            "Treat the answer as internal research assistance."
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
        if session_id in self.store:
            self.store.move_to_end(session_id)
            return self.store[session_id]
        self.store[session_id] = ChatMessageHistory()
        while len(self.store) > self.max_sessions:
            self.store.popitem(last=False)
        return self.store[session_id]

    def conversational(self, query: str, session_id: str) -> dict:
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
        answer = str(response.get("answer", "")).strip()
        if not sources:
            answer = NO_SUPPORT_ANSWER
        return {
            "answer": answer,
            "sources": sources,
            "grounding": grounding_status(sources),
            "query": query.strip(),
            "session_id": session_id.strip(),
        }
