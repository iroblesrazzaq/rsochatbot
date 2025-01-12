#!/usr/bin/env python3
# api/test_bot.py
from rso_bot import RSORagBot
import os
from dotenv import load_dotenv
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_bot():
    try:
        # Get the directory containing this script
        script_dir = Path(__file__).parent.absolute()
        # Look for .env in the parent directory (project root)
        env_path = script_dir.parent / '.env'
        
        # Load environment variables from the correct path
        load_dotenv(dotenv_path=env_path)
        logger.info(f"Looking for .env file at: {env_path}")
        
        # Check environment variables
        pinecone_key = os.getenv('PINECONE_API_KEY')
        groq_key = os.getenv('GROQ_API_KEY')
        
        if not pinecone_key or not groq_key:
            print("Error: Missing API keys")
            print(f"Searched for .env file at: {env_path}")
            return
            
        print("Initializing bot...")
        bot = RSORagBot(
            pinecone_api_key=pinecone_key,
            pinecone_index_name="rso-chatbot",
            groq_api_key=groq_key
        )
        
        # Test query
        test_query = "I'm interested in computer science clubs"
        print(f"\nTesting with query: {test_query}")
        
        print("\nGetting response...")
        response = bot.generate_response(test_query)
        
        print("\nResponse received:")
        print(response)
        
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    test_bot()