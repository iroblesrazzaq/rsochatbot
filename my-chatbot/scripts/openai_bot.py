#!/usr/bin/env python3
# scripts/openai_bot.py

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
import tiktoken
from collections import defaultdict
import pickle
from functools import lru_cache

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class ContextManager:
    """Handles context processing and caching for the ChatBot."""
    
    def __init__(self, json_file: str):
        self.json_file = json_file
        self.cache_file = Path(f"{json_file}_context.pkl")
        self.max_context_tokens = 120000
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        
    def _load_json_data(self) -> List[Dict[str, Any]]:
        """Load RSO data from JSON file."""
        script_dir = Path(__file__).parent.absolute()
        json_path = script_dir / f"{self.json_file}.json"
        
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
            
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _process_rso_data(self, rso_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Process RSO data into category groups with optimized structure."""
        category_groups = defaultdict(list)
        
        for rso in rso_data:
            categories = rso.get('categories', [])
            if not categories:
                ai_cats = rso.get('ai_categories', [])
                if ai_cats:
                    categories = [max(ai_cats, key=lambda x: x['confidence'])['name']]
                else:
                    categories = ['Uncategorized']
            
            # Create a streamlined RSO entry with only necessary fields
            processed_rso = {
                'name': rso.get('name', 'N/A'),
                'description': rso.get('full_description') or rso.get('description_preview', 'N/A'),
                'website': rso.get('full_url'),
                'contact': rso.get('contact', {}).get('email'),
                'social_media': {k: v for k, v in rso.get('social_media', {}).items() if v and v.lower() not in ['none', 'n/a', '']},
                'meetings': rso.get('additional_info', {}).get('Regular Meetings (Day/Time/Location):')
            }
            
            for category in categories:
                category_groups[category].append(processed_rso)
                
        return dict(category_groups)

    def _format_context(self, category_groups: Dict[str, List[Dict[str, Any]]]) -> str:
        """Format processed data into context string."""
        context_parts = ["Here is the information about UChicago RSOs (Registered Student Organizations) by category:\n\n"]
        
        for category, rsos in category_groups.items():
            category_section = [f"Category: {category}\n"]
            
            for rso in rsos:
                rso_info = [f"\nName: {rso['name']}",
                           f"Description: {rso['description']}"]
                
                if rso['website']:
                    rso_info.append(f"Website: {rso['website']}")
                if rso['contact']:
                    rso_info.append(f"Contact: {rso['contact']}")
                if rso['social_media']:
                    links = [f"{platform}: {url}" for platform, url in rso['social_media'].items()]
                    rso_info.append(f"Social Media: {', '.join(links)}")
                if rso['meetings']:
                    rso_info.append(f"Meetings: {rso['meetings']}")
                    
                rso_info.append("---")
                category_section.append("\n".join(rso_info))
                
            context_parts.append("\n".join(category_section))
            
        return "\n\n".join(context_parts)

    def get_processed_context(self) -> str:
        """Get processed context, using cache if available."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'rb') as f:
                    context = pickle.load(f)
                    logger.info("Loaded context from cache")
                    return context
        except Exception as e:
            logger.warning(f"Cache load failed, regenerating context: {e}")

        # Process context from scratch
        rso_data = self._load_json_data()
        category_groups = self._process_rso_data(rso_data)
        context = self._format_context(category_groups)
        
        # Truncate if necessary
        tokens = self.tokenizer.encode(context)
        if len(tokens) > self.max_context_tokens:
            logger.warning(f"Context too long ({len(tokens)} tokens). Truncating...")
            context = self.tokenizer.decode(tokens[:self.max_context_tokens])
        
        # Save to cache
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(context, f)
                logger.info("Saved context to cache")
        except Exception as e:
            logger.warning(f"Failed to save context cache: {e}")
        
        return context

class ChatBot:
    def __init__(self, openai_api_key: Optional[str] = None, json_file: str = "categorized_rsos2"):
        """Initialize the ChatBot with OpenAI API key and JSON data file."""
        try:
            # Load environment variables
            script_dir = Path(__file__).parent.absolute()
            env_path = script_dir.parent / '.env'
            load_dotenv(dotenv_path=env_path)
            
            # Set up OpenAI client
            self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
            if not self.api_key:
                raise ValueError("OpenAI API key not found")
            
            self.client = OpenAI(api_key=self.api_key)
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
            
            # Initialize context manager
            self.context_manager = ContextManager(json_file)
            self._initialize_system_prompt()
            
            logger.info("ChatBot initialization complete!")
            
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}", exc_info=True)
            raise

    def _initialize_system_prompt(self) -> None:
        """Initialize the system prompt with processed context."""
        context = self.context_manager.get_processed_context()
        self.system_prompt = f"""You are a helpful assistant that helps University of Chicago students find and learn about 
        Registered Student Organizations (RSOs). Use the provided information about RSOs to answer questions accurately. 
        If asked about RSOs that aren't in the provided data, let the student know you can only provide information 
        about RSOs in your database.

        When recommending RSOs:
        1. Consider any specific interests or preferences mentioned in the query
        2. Group recommendations by category when appropriate
        3. Provide relevant details like contact information, meeting times, and websites when available
        4. If the student's interests match multiple categories, mention diverse options

        Here's the RSO information you should use:
        
        {context}"""

    @lru_cache(maxsize=1000)
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text with caching."""
        return len(self.tokenizer.encode(text))

    def generate_response(self, query: str) -> str:
        """Generate a response to the user's query."""
        try:
            logger.info(f"Generating response for query: {query}")
            
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            return f"I apologize, but I encountered an error while processing your question: {str(e)}"

# Global bot instance with lazy initialization
_bot_instance = None

def get_bot_instance() -> ChatBot:
    """Get or create a singleton instance of ChatBot."""
    global _bot_instance
    if _bot_instance is None:
        try:
            logger.info("Creating new ChatBot instance...")
            _bot_instance = ChatBot()
        except Exception as e:
            logger.error(f"Error creating ChatBot instance: {str(e)}", exc_info=True)
            raise
    return _bot_instance

def main() -> None:
    """Main function to handle command line queries."""
    try:
        if len(sys.argv) < 2:
            print(json.dumps({"error": "No query provided"}))
            return

        query = sys.argv[1]
        logger.info(f"Processing query: {query}")
        
        bot = get_bot_instance()
        response = bot.generate_response(query)
        print(json.dumps({"response": response}))
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()