#!/usr/bin/env python3
import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SharedBotResources:
    """Manages expensive resources that should be shared across bot instances"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize shared resources once"""
        try:
            logger.info("Initializing shared bot resources...")
            
            # Load environment variables
            script_dir = Path(__file__).parent.absolute()
            env_path = script_dir.parent / '.env'
            load_dotenv(dotenv_path=env_path)
            
            # Initialize Pinecone (shared across instances)
            self.pinecone_api_key = os.getenv('PINECONE_API_KEY')
            if not self.pinecone_api_key:
                raise ValueError("Pinecone API key not found")
                
            import pinecone
            self.pc = pinecone.Pinecone(api_key=self.pinecone_api_key)
            self.index = self.pc.Index(os.getenv('PINECONE_INDEX_NAME', 'rso-chatbot'))
            
            # Initialize embedding model (shared across instances)
            from sentence_transformers import SentenceTransformer
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            self.embed_model = SentenceTransformer('all-mpnet-base-v2')
            
            logger.info("Shared resources initialization complete!")
            
        except Exception as e:
            logger.error(f"Error initializing shared resources: {str(e)}")
            raise

class HybridRsoBot:
    """Handles RSO chat interactions with shared resource management"""
    
    def __init__(self, chat_id: str):
        """
        Initialize a new RSO bot instance
        
        Args:
            chat_id: Unique identifier for this chat session
        """
        try:
            self.chat_id = chat_id
            logger.info(f"Initializing RSO bot for chat {chat_id}")
            
            # Get shared resources
            self.shared = SharedBotResources()
            
            # Initialize chat-specific components
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not found")
                
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            
            # Initialize chat state
            self.conversation_history = []
            
            logger.info(f"RSO bot {chat_id} initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing RSO bot: {str(e)}")
            raise

    def get_relevant_contexts(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Get relevant RSO contexts using shared embedding model and Pinecone index
        
        Args:
            query: The search query
            top_k: Number of results to return
            
        Returns:
            List of matching RSOs with their metadata
        """
        try:
            logger.info(f"Searching for RSOs with query: {query}")
            
            # Use shared embedding model
            query_embedding = self.shared.embed_model.encode(query).tolist()
            
            # Use shared Pinecone index
            results = self.shared.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            logger.info(f"Found {len(results.matches)} matching RSOs")
            return results.matches
            
        except Exception as e:
            logger.error(f"Error in get_relevant_contexts: {str(e)}")
            return []

    def format_context(self, relevant_rsos: List[Dict[str, Any]]) -> str:
        """Format RSO information for the LLM prompt"""
        if not relevant_rsos:
            return "No relevant RSOs found in the database."
        
        context = []
        for rso in relevant_rsos:
            metadata = rso.metadata
            rso_info = []
            
            # Required fields
            rso_info.append(f"Name: {metadata.get('name', 'N/A')}")
            rso_info.append(f"Description: {metadata.get('description', 'N/A')}")
            
            # Optional fields with validation
            if categories := metadata.get('categories'):
                if isinstance(categories, list):
                    rso_info.append(f"Categories: {', '.join(categories)}")
            
            if contact := metadata.get('contact_email'):
                if contact.lower() not in ['none', 'n/a', '']:
                    rso_info.append(f"Contact: {contact}")
            
            if website := metadata.get('full_url'):
                if website.lower() not in ['none', 'n/a', '']:
                    rso_info.append(f"Website: {website}")
                    
            context.append("\n".join(rso_info))
        
        return "\n\n---\n\n".join(context)

    async def generate_response(self, query: str) -> str:
        """
        Generate a response using the OpenAI API
        
        Args:
            query: The user's question
            
        Returns:
            Generated response string
        """
        try:
            # Get relevant contexts using shared resources
            relevant_rsos = self.get_relevant_contexts(query)
            context = self.format_context(relevant_rsos)
            
            # Create the prompt
            system_prompt = """You are a knowledgeable assistant for University of Chicago students, 
            specializing in Registered Student Organizations (RSOs). Your role is to help students 
            learn about and engage with RSOs by providing accurate, detailed information."""
            
            user_prompt = f"""Here is a student's question about UChicago RSOs: "{query}"
            
            Based on the query, here are relevant RSOs from our database:
            
            {context}
            
            Please provide a natural, conversational response that:
            1. Directly addresses their specific question or need
            2. Only mentions RSOs that are truly relevant to their query
            3. Provides specific, actionable information when available
            4. Acknowledges if the available information might not fully answer their question"""
            
            # Generate response using chat-specific OpenAI client
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Update conversation history
            self.conversation_history.append({
                "query": query,
                "response": response.choices[0].message.content
            })
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"I apologize, but I encountered an error while processing your question: {str(e)}"

    def cleanup(self):
        """Cleanup chat-specific resources"""
        logger.info(f"Cleaning up RSO bot {self.chat_id}")
        self.conversation_history.clear()

# Global bot manager
_bots: Dict[str, HybridRsoBot] = {}
_bot_lock = threading.Lock()

def get_bot(chat_id: str) -> HybridRsoBot:
    """
    Get or create a bot instance for a chat session
    
    Args:
        chat_id: Unique identifier for the chat session
        
    Returns:
        HybridRsoBot instance
    """
    with _bot_lock:
        if chat_id not in _bots:
            _bots[chat_id] = HybridRsoBot(chat_id)
        return _bots[chat_id]