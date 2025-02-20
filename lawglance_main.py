#adding necessary imports
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.prompts import ChatPromptTemplate
from langchain.chains import create_history_aware_retriever
from langchain_core.prompts import MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
import json
import os
import datetime

#This Class deals with working of Chatbot

class Lawglance: 
    """This is the class which deals mainly with a conversational RAG
    It takes llm, embeddings and vector store as input to initialise.

    create an instance of it using law = LawGlance(llm,embeddings,vectorstore)
    In order to run the instance

    law.conversational(query)

    Example:
    law = LawGlance(llm,embeddings,vectorstore)
    query1 = "What is rule of Law?"
    law.conversational(query1)
    query2 = "Is it applicable in India?"
    law.conversational(query2)
    """
    store = {}

    def __init__(self, llm, embeddings, vector_store, 
                calendar_client_config=None, comm_creds=None, legal_db_url=None):
        self.llm = llm
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.step_count = 0
        
        # Initialize new components
        from calendar_manager import CalendarManager
        from communication_handler import CommunicationHandler
        from research_enhancer import ResearchEnhancer
        from auth_handler import AuthHandler
        
        self.auth_handler = AuthHandler(calendar_client_config) if calendar_client_config else None
        self.calendar = CalendarManager() if calendar_client_config else None
        self.comm_handler = CommunicationHandler(**comm_creds) if comm_creds else None
        self.research = ResearchEnhancer(legal_db_url) if legal_db_url else None
        
        self.load_state()

    def __retriever(self):
        """The function to define the properties of retriever"""
        retriever = self.vector_store.as_retriever(search_type="similarity_score_threshold",search_kwargs={"k": 20, "score_threshold":0.2})
        return retriever
    
    def llm_answer_generator(self,query):
        llm = self.llm
        retriever = self.__retriever()
        contextualize_q_system_prompt = (
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, "
            "just reformulate it if needed and otherwise return it as is."
        )

        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        history_aware_retriever = create_history_aware_retriever(
            llm, retriever, contextualize_q_prompt
        )
        system_prompt = (
            "You are a helpful legal assistant who is tasked with answering the following question based on the provided context: {input}")
        qa_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", """You are provided with some context containing legal contents that might include
            relevant sections or articles which can help you answer the question.
            Your task is to answer the question based on the context.
            Ensure that the answer is derived from the relevant parts of the context only.
            \n\nRelevant Context: \n"
            {context}

            Please return only the answer as output."""),
                ]
            )

        question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
        return rag_chain

    def get_session_history(self,session_id: str) -> BaseChatMessageHistory:
        if session_id not in Lawglance.store:
            Lawglance.store[session_id] = ChatMessageHistory()
        return Lawglance.store[session_id]
    
    def save_state(self):
        """Save current state to file with rotation and validation"""
        try:
            # Maintain previous state as backup
            if os.path.exists('ai_state.json'):
                os.rename('ai_state.json', 'ai_state_prev.json')
                
            # Create validated state snapshot
            state = {
                'store': self.store,
                'step_count': self.step_count,
                'timestamp': datetime.datetime.now().isoformat(),
                'system_status': 'operational'
            }
            
            # Validate critical state data
            if not isinstance(state['step_count'], int) or state['step_count'] < 0:
                raise ValueError(f"Invalid step count: {state['step_count']}")
            if not isinstance(state['store'], dict):
                raise TypeError("Store must be a dictionary")
                
            # Write new state with atomic replacement
            with open('ai_state.tmp', 'w') as f:
                json.dump(state, f, indent=2)
            os.replace('ai_state.tmp', 'ai_state.json')
            
            print(f"State persisted successfully at {state['timestamp']}")
            
        except Exception as e:
            print(f"State preservation failed: {str(e)}")
            # Restore previous state if available
            if os.path.exists('ai_state_prev.json'):
                os.rename('ai_state_prev.json', 'ai_state.json')
                print("Restored previous state file")

    def load_state(self):
        """Load and validate state from file with fallback"""
        try:
            # Try loading primary state file
            if os.path.exists('ai_state.json'):
                with open('ai_state.json', 'r') as f:
                    state = json.load(f)
                    
                # Validate loaded state
                required_fields = ['store', 'step_count', 'timestamp']
                if not all(field in state for field in required_fields):
                    raise ValueError("Missing required state fields")
                    
                if not isinstance(state['store'], dict):
                    raise TypeError("Invalid store format")
                    
                if not isinstance(state['step_count'], int) or state['step_count'] < 0:
                    raise ValueError(f"Invalid step count: {state['step_count']}")
                    
                # Check timestamp freshness (within 7 days)
                state_time = datetime.datetime.fromisoformat(state['timestamp'])
                if (datetime.datetime.now() - state_time).days > 7:
                    print("Warning: Loading state older than 7 days")
                    
                self.store = state['store']
                self.step_count = state['step_count']
                print(f"Loaded valid state from {state['timestamp']}")
                
            elif os.path.exists('ai_state_prev.json'):
                print("Loading from backup state")
                os.rename('ai_state_prev.json', 'ai_state.json')
                self.load_state()
                
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"State validation failed: {str(e)}")
            if os.path.exists('ai_state_prev.json'):
                print("Attempting backup load")
                os.rename('ai_state_prev.json', 'ai_state.json')
                self.load_state()

    def conversational(self, query):
        # Handle authentication flow
        if 'connect calendar' in query.lower() and self.auth_handler:
            self.auth_handler.start_server()
            return f"Please visit: {self.auth_handler.get_auth_url()}"
            
        # Check for calendar-related queries
        if 'schedule' in query.lower() or 'meeting' in query.lower():
            return self._handle_calendar_request(query)
            
        # Original RAG processing
        rag_chain = self.llm_answer_generator(query)
        self.step_count += 1
        if self.step_count % 3 == 0:
            self.save_state()

        get_session_history = self.get_session_history
        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer")
        response = conversational_rag_chain.invoke(
            {"input": query},
            config={
                "configurable": {"session_id": "abc123"}
            },
        )
        return response['answer']
    
    def _handle_calendar_request(self, query):
        if not self.calendar:
            return "Calendar integration not configured"
            
        # Simple NLP for scheduling
        if 'list' in query.lower():
            events = self.calendar.list_events()
            return "\n".join([e['summary'] for e in events[:5]]) or "No upcoming events"
            
        if 'create' in query.lower():
            # Extract time from query (simplified)
            time_str = " ".join(query.split()[-3:])  # Last 3 words as time
            try:
                event_time = datetime.datetime.strptime(time_str, "%B %d %Y")
                self.calendar.create_event("Legal Meeting", event_time)
                return f"Meeting scheduled for {event_time.strftime('%b %d %Y')}"
            except ValueError:
                return "Could not parse time. Please use format 'Month Day Year'"
                
        return "Calendar request not understood"
    
    def finalize_auth(self):
        if self.auth_handler and self.auth_handler.auth_code:
            token_info = self.auth_handler.exchange_code()
            self.calendar.save_credentials(token_info)
            return "Calendar connected successfully"
        return "No pending authentication"
