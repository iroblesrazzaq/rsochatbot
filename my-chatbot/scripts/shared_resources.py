#!/usr/bin/env python3
import os
import threading
import logging
from pathlib import Path
from sentence_transformers import SentenceTransformer
import pinecone
from dotenv import load_dotenv
import tiktoken
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SharedResources:
    """
    A singleton class that manages shared resources across all chat instances.
    This includes heavy models and API clients that should only be loaded once.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize all shared resources with proper error handling"""
        try:
            logger.info("Initializing shared resources...")
            
            # Load environment variables
            script_dir = Path(__file__).parent.absolute()
            env_path = script_dir.parent / '.env'
            load_dotenv(dotenv_path=env_path)
            
            # Initialize embedding model
            logger.info("Loading sentence transformer model...")
            self.embed_model = SentenceTransformer('all-mpnet-base-v2')
            
            # Initialize Pinecone client
            logger.info("Initializing Pinecone client...")
            self.pinecone_api_key = os.getenv('PINECONE_API_KEY')
            if not self.pinecone_api_key:
                raise ValueError("Pinecone API key not found in environment variables")
                
            self.pinecone_client = pinecone.Pinecone(api_key=self.pinecone_api_key)
            self.pinecone_index_name = os.getenv('PINECONE_INDEX_NAME', 'rso-chatbot')
            self.pinecone_index = self.pinecone_client.Index(self.pinecone_index_name)
            
            # Initialize tokenizer
            logger.info("Initializing tokenizer...")
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
            
            logger.info("Shared resources initialization complete!")
            
        except Exception as e:
            logger.error(f"Error initializing shared resources: {str(e)}")
            raise

    @lru_cache(maxsize=1000)
    def get_embedding(self, text: str) -> list[float]:
        """
        Get embeddings for text with caching.
        
        Args:
            text: The text to embed
            
        Returns:
            List of embedding values
        """
        return self.embed_model.encode(text).tolist()

    def cleanup(self):
        """Cleanup any resources that need explicit cleanup"""
        logger.info("Cleaning up shared resources...")
        # Add any cleanup code here if needed in the future