#!/usr/bin/env python3
import pinecone
from sentence_transformers import SentenceTransformer
from groq import Groq
import os
from dotenv import load_dotenv
import sys
import json
import logging
from pathlib import Path
import time
from typing import List, Dict, Optional, Any, Union

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Get the directory containing this script
script_dir = Path(__file__).parent.absolute()
env_path = script_dir.parent / '.env'

# Load environment variables
load_dotenv(dotenv_path=env_path)

# Global bot instance
_bot_instance = None

class RSORagBot:
    def __init__(self, pinecone_api_key: Optional[str] = None, 
                 pinecone_index_name: Optional[str] = None, 
                 groq_api_key: Optional[str] = None):
        """
        Initialize the RSO bot with API keys and necessary clients
        """
        try:
            # Get API keys from parameters or environment
            self.pinecone_api_key = pinecone_api_key or os.getenv('PINECONE_API_KEY')
            self.groq_api_key = groq_api_key or os.getenv('GROQ_API_KEY')
            self.pinecone_index_name = pinecone_index_name or os.getenv('PINECONE_INDEX_NAME', 'rso-chatbot')

            if not self.pinecone_api_key:
                raise ValueError("Pinecone API key not found")
            if not self.groq_api_key:
                raise ValueError("Groq API key not found")

            # Initialize Pinecone
            self.pc = pinecone.Pinecone(api_key=self.pinecone_api_key)
            self.index = self.pc.Index(self.pinecone_index_name)
            
            # Initialize embedding model
            self.embed_model = SentenceTransformer('all-mpnet-base-v2')
            
            # Initialize Groq client
            self.groq_client = Groq(api_key=self.groq_api_key)
            
            # Define system prompt
            self.system_prompt = """You are a knowledgeable and helpful assistant for University of Chicago students, 
            specializing in Registered Student Organizations (RSOs). Your role is to help students learn about and 
            engage with RSOs by:

            - Providing accurate, detailed information about specific RSOs when asked
            - Recommending relevant RSOs based on students' interests and preferences
            - Explaining RSO activities, events, and opportunities
            - Helping with general RSO-related questions
            - Clarifying any confusion about RSOs or the membership process

            Focus on addressing the student's specific question while maintaining a helpful and informative tone.
            If you're not sure about specific details, be honest about what you don't know."""

        except Exception as e:
            logger.error(f"Initialization error: {str(e)}", exc_info=True)
            raise

    def get_relevant_rsos(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Get relevant RSOs based on the query
        
        Args:
            query: The search query
            top_k: Number of results to return
            
        Returns:
            List of matching RSOs with their metadata
        """
        try:
            logger.info(f"Searching for RSOs with query: {query}")
            query_embedding = self.embed_model.encode(query).tolist()
            
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            logger.info(f"Found {len(results.matches)} matching RSOs")
            return results.matches
            
        except Exception as e:
            logger.error(f"Error in get_relevant_rsos: {str(e)}", exc_info=True)
            return []

    def format_context(self, relevant_rsos: List[Dict[str, Any]]) -> str:
        """
        Format RSO information into a context string for the LLM
        
        Args:
            relevant_rsos: List of RSO matches with metadata
            
        Returns:
            Formatted context string
        """
        try:
            if not relevant_rsos:
                return "No relevant RSOs found in the database."
            
            context = "Here is the RSO information:\n\n"
            
            for rso in relevant_rsos:
                metadata = rso.metadata
                try:
                    # Required fields
                    context += f"Name: {metadata.get('name', 'N/A')}\n"
                    context += f"Description: {metadata.get('description', 'N/A')}\n"
                    
                    # Optional fields with validation
                    categories = metadata.get('categories', [])
                    if categories and isinstance(categories, list):
                        context += f"Categories: {', '.join(categories)}\n"
                    
                    contact = metadata.get('contact_email')
                    if contact and contact.lower() not in ['none', 'n/a', '']:
                        context += f"Contact: {contact}\n"
                    
                    social_media = metadata.get('social_media_links', [])
                    if social_media and isinstance(social_media, list):
                        context += f"Social Media: {', '.join(social_media)}\n"
                    
                    additional_info = metadata.get('additional_info', [])
                    if additional_info and isinstance(additional_info, list):
                        context += f"Additional Info: {', '.join(additional_info)}\n"
                    
                    website = metadata.get('full_url')
                    if website and website.lower() not in ['none', 'n/a', '']:
                        context += f"Website: {website}\n"
                    
                    context += "\n"
                    
                except Exception as e:
                    logger.error(f"Error formatting RSO metadata: {str(e)}", exc_info=True)
                    continue
            
            return context
            
        except Exception as e:
            logger.error(f"Error in format_context: {str(e)}", exc_info=True)
            return "Error formatting RSO information."

    def generate_response(self, query: str) -> str:
        """
        Generate a response based on the query and relevant RSO information
        
        Args:
            query: The user's question or request
            
        Returns:
            Generated response string
        """
        try:
            # Normalize query
            normalized_query = query.lower().replace('club', 'rso')
            logger.info(f"Original query: {query}")
            logger.info(f"Normalized query: {normalized_query}")

            # Get relevant RSOs
            relevant_rsos = self.get_relevant_rsos(normalized_query)
            
            # Format context
            context = self.format_context(relevant_rsos)
            
            # Construct prompt
            prompt = f"""Here is a student's question about UChicago RSOs: "{query}"

            Based on the query, here are relevant RSOs from our database:

            {context}

            Please provide a natural, conversational response that:
            1. Directly addresses their specific question or need
            2. Only mentions RSOs that are truly relevant to their query
            3. Provides specific, actionable information when available
            4. Acknowledges if the available information might not fully answer their question

            If their question isn't about finding RSOs, focus on answering their question rather than listing RSOs."""
            
            # Get response from Groq
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model="mixtral-8x7b-32768",
                temperature=0.7,
                max_tokens=1024
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in generate_response: {str(e)}", exc_info=True)
            return f"I apologize, but I encountered an error while processing your question. Please try asking again or rephrase your question."

def get_bot_instance() -> RSORagBot:
    """Get or create a singleton instance of RSORagBot"""
    global _bot_instance
    if _bot_instance is None:
        try:
            logger.info("Creating new RSORagBot instance")
            _bot_instance = RSORagBot()
            logger.info("RSORagBot instance created successfully")
        except Exception as e:
            logger.error(f"Error creating RSORagBot instance: {str(e)}", exc_info=True)
            raise
    return _bot_instance

def main() -> None:
    """Main function to handle command line queries"""
    try:
        if len(sys.argv) < 2:
            error_msg = {"error": "No query provided"}
            logger.error("No query provided")
            print(json.dumps(error_msg))
            return

        query = sys.argv[1]
        logger.info(f"Processing query: {query}")
        
        # Get or create bot instance
        bot = get_bot_instance()
        
        # Generate response
        start_time = time.time()
        response = bot.generate_response(query)
        total_time = time.time() - start_time
        
        logger.info(f"Total processing time: {total_time:.2f} seconds")
        print(json.dumps({"response": response}))
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()