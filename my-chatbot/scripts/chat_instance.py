#!/usr/bin/env python3
import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from shared_resources import SharedResources

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatInstance:
    """
    Represents a single chat instance that manages conversation state
    while using shared resources for heavy operations.
    """
    def __init__(self, chat_id: str):
        """
        Initialize a new chat instance.
        
        Args:
            chat_id: Unique identifier for this chat session
        """
        try:
            self.chat_id = chat_id
            logger.info(f"Initializing chat instance {chat_id}")
            
            # Load environment variables
            script_dir = Path(__file__).parent.absolute()
            env_path = script_dir.parent / '.env'
            load_dotenv(dotenv_path=env_path)
            
            # Get shared resources
            self.shared = SharedResources()
            
            # Initialize chat-specific components
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not found")
            
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            
            # Initialize chat state
            self.conversation_history = []
            
            logger.info(f"Chat instance {chat_id} initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing chat instance {chat_id}: {str(e)}")
            raise

    async def get_relevant_contexts(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Get relevant RSO contexts using shared embedding model and Pinecone index.
        
        Args:
            query: The search query
            top_k: Number of results to return
            
        Returns:
            List of matching RSOs with their metadata
        """
        try:
            logger.info(f"Searching for relevant RSOs with query: {query}")
            
            # Use shared resources for embedding
            query_embedding = self.shared.get_embedding(query)
            
            # Use shared Pinecone index for search
            results = self.shared.pinecone_index.query(
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
        # Your existing format_context code here
        pass

    async def generate_response(self, query: str) -> str:
        """
        Generate a response using the OpenAI API.
        Maintains chat-specific context while using shared resources for embeddings and search.
        
        Args:
            query: The user's question
            
        Returns:
            Generated response string
        """
        try:
            # Get relevant contexts using shared resources
            relevant_rsos = await self.get_relevant_contexts(query)
            context = self.format_context(relevant_rsos)
            
            # Create the prompt
            prompt = self._create_prompt(query, context)
            
            # Generate response using chat-specific OpenAI client
            response = self.openai_client.chat.completions.create(
                model="gpt-4",  # or your chosen model
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
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

    def _get_system_prompt(self) -> str:
        """Return the system prompt for this chat instance"""
        return """You are a knowledgeable assistant for University of Chicago students, 
        specializing in Registered Student Organizations (RSOs)..."""

    def _create_prompt(self, query: str, context: str) -> str:
        """Create a prompt for the LLM using the query and context"""
        return f"""Here is a student's question about UChicago RSOs: "{query}"
        
        Based on the query, here are relevant RSOs from our database:
        
        {context}
        
        Please provide a natural, conversational response that addresses their specific question."""

    def cleanup(self):
        """Cleanup chat-specific resources"""
        logger.info(f"Cleaning up chat instance {self.chat_id}")
        self.conversation_history.clear()