#!/usr/bin/env python3
#!/usr/bin/env python3
import pinecone
from sentence_transformers import SentenceTransformer
import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
import tiktoken
import time
import asyncio
from functools import lru_cache
import threading

# Set environment variable to handle tokenizer warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class ModelCache:
    """Singleton class to cache models and expensive operations"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize models and connections once"""
        logger.info("Initializing model cache...")
        self.embed_model = SentenceTransformer('all-mpnet-base-v2')
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        logger.info("Model cache initialization complete")

class HybridRsoBot:
    def __init__(self, 
                 pinecone_api_key: Optional[str] = None,
                 pinecone_index_name: Optional[str] = None,
                 openai_api_key: Optional[str] = None):
        """Initialize the Hybrid RSO bot with cached models"""
        try:
            # Load environment variables
            script_dir = Path(__file__).parent.absolute()
            env_path = script_dir.parent.parent / '.env'
            load_dotenv(dotenv_path=env_path)
            
            # Set up API keys
            self.pinecone_api_key = pinecone_api_key or os.getenv('PINECONE_API_KEY')
            self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
            self.pinecone_index_name = pinecone_index_name or os.getenv('PINECONE_INDEX_NAME', 'rso-chatbot')

            if not self.pinecone_api_key:
                raise ValueError("Pinecone API key not found")
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not found")

            # Initialize Pinecone
            self.pc = pinecone.Pinecone(api_key=self.pinecone_api_key)
            self.index = self.pc.Index(self.pinecone_index_name)
            
            # Get cached models
            self.model_cache = ModelCache()
            
            # Initialize OpenAI client
            self.client = OpenAI(api_key=self.openai_api_key)
            
            logger.info("HybridRsoBot initialization complete!")
            
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}", exc_info=True)
            raise

    @lru_cache(maxsize=100)
    def _get_embedding(self, text: str) -> List[float]:
        """Cache embeddings for repeated queries"""
        return self.model_cache.embed_model.encode(text).tolist()

    async def get_relevant_contexts(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Asynchronously get relevant RSO contexts"""
        try:
            logger.info(f"Searching for relevant RSOs with query: {query}")
            query_embedding = await asyncio.to_thread(self._get_embedding, query)
            
            results = await asyncio.to_thread(
                self.index.query,
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            logger.info(f"Found {len(results.matches)} matching RSOs")
            return results.matches
            
        except Exception as e:
            logger.error(f"Error in get_relevant_contexts: {str(e)}", exc_info=True)
            return []

    def format_rso_contexts(self, relevant_rsos: List[Dict[str, Any]]) -> str:
        """Format RSO information efficiently"""
        if not relevant_rsos:
            return "No relevant RSOs found in the database."
        
        # Pre-allocate lists for better memory efficiency
        contexts = []
        for rso in relevant_rsos:
            metadata = rso.metadata
            rso_info = [f"Name: {metadata.get('name', 'N/A')}",
                       f"Description: {metadata.get('description', 'N/A')}"]
            
            # Optional fields
            if categories := metadata.get('categories'):
                if isinstance(categories, list):
                    rso_info.append(f"Categories: {', '.join(categories)}")
            
            if contact := metadata.get('contact_email'):
                if contact.lower() not in ['none', 'n/a', '']:
                    rso_info.append(f"Contact: {contact}")
            
            if website := metadata.get('full_url'):
                if website.lower() not in ['none', 'n/a', '']:
                    rso_info.append(f"Website: {website}")
            
            if social_media := metadata.get('social_media_links'):
                if isinstance(social_media, list) and social_media:
                    rso_info.append(f"Social Media: {', '.join(social_media)}")
            
            if additional_info := metadata.get('additional_info'):
                if isinstance(additional_info, list) and additional_info:
                    rso_info.append(f"Additional Info: {', '.join(additional_info)}")
            
            contexts.append("\n".join(rso_info))
        
        return "\n\n---\n\n".join(contexts)

    def create_system_prompt(self, context: str) -> str:
        """Create system prompt template"""
        return f"""
        INSTRUCTION:
        You are a helpful assistant that helps University of Chicago students find and learn about 
        Registered Student Organizations (RSOs). Use the provided information about RSOs to answer questions accurately. 
        If asked about RSOs that aren't in the provided data, let the student know you can only provide information 
        about RSOs in your database.

        DOCUMENTS:
        {context}"""

    async def generate_response(self, query: str) -> str:
        """Generate response using async operations where possible"""
        try:
            logger.info(f"Processing query: {query}")
            start_time = time.time()
            
            # Get relevant contexts using RAG
            relevant_rsos = await self.get_relevant_contexts(query)
            context = self.format_rso_contexts(relevant_rsos)
            
            # Create system prompt
            system_prompt = self.create_system_prompt(context)
            
            # Generate response using ChatGPT
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"QUESTION: {query}"}
                ],
                temperature=0.7,
                max_tokens=5000
            )
            
            total_time = time.time() - start_time
            logger.info(f"Response generated in {total_time:.2f} seconds")
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            return f"I apologize, but I encountered an error while processing your question: {str(e)}"

# Global bot instance with thread-safe initialization
_bot_instance = None
_bot_lock = threading.Lock()

def get_bot_instance() -> HybridRsoBot:
    """Thread-safe singleton instance of HybridRsoBot"""
    global _bot_instance
    with _bot_lock:
        if _bot_instance is None:
            try:
                logger.info("Creating new HybridRsoBot instance...")
                _bot_instance = HybridRsoBot()
            except Exception as e:
                logger.error(f"Error creating HybridRsoBot instance: {str(e)}", exc_info=True)
                raise
    return _bot_instance

async def main() -> None:
    """Async main function to handle queries"""
    try:
        if len(sys.argv) < 2:
            print(json.dumps({"error": "No query provided"}))
            return

        query = sys.argv[1]
        logger.info(f"Processing query: {query}")
        
        bot = get_bot_instance()
        response = await bot.generate_response(query)
        print(json.dumps({"response": response}))
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    asyncio.run(main())