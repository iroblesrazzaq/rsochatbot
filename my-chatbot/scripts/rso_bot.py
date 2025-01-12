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
    def __init__(self, pinecone_api_key=None, pinecone_index_name=None, groq_api_key=None):
        try:
            start_time = time.time()
            logger.info("Starting RSORagBot initialization...")
            
            self.pinecone_api_key = pinecone_api_key or os.getenv('PINECONE_API_KEY')
            self.groq_api_key = groq_api_key or os.getenv('GROQ_API_KEY')
            self.pinecone_index_name = pinecone_index_name or "rso-chatbot"
            
            if not self.pinecone_api_key:
                raise ValueError("Pinecone API key not found")
            if not self.groq_api_key:
                raise ValueError("Groq API key not found")
            
            logger.info("Connecting to Pinecone...")
            self.pc = pinecone.Pinecone(api_key=self.pinecone_api_key)
            self.index = self.pc.Index(self.pinecone_index_name)
            logger.info("Pinecone connection established")
            
            logger.info("Loading embedding model...")
            self.embed_model = SentenceTransformer('all-mpnet-base-v2')
            logger.info("Embedding model loaded")
            
            logger.info("Initializing Groq client...")
            self.groq_client = Groq(api_key=self.groq_api_key)
            logger.info("Groq client initialized")
            
            self.system_prompt = """You are a knowledgeable and helpful assistant for University of Chicago students, 
        specializing in Registered Student Organizations (RSOs). Your role is to help students learn about and 
        engage with RSOs by:

        - Providing accurate, detailed information about specific RSOs, only when asked
        - Recommending relevant RSOs based on students' interests and preferences, only when asked
        - Explaining RSO activities, events, and opportunities

        Focus on the specific information or guidance the student is seeking."""
            
            init_time = time.time() - start_time
            logger.info(f"RSORagBot initialization completed in {init_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error during initialization: {str(e)}", exc_info=True)
            raise

    def analyze_query_intent(self, query):
        """Analyze the query to determine the type of response needed"""
        try:
            logger.info(f"Analyzing query intent: {query}")
            
            intent_prompt = f"""Analyze this student query: "{query}"
            Determine the type of question and what information is needed to provide a helpful response.
            Return your analysis in JSON format with these fields:
            - query_type: [specific_info, comparison, recommendation, general_info, other]
            - needs_rso_lookup: boolean
            - search_terms: list of relevant terms if RSO lookup needed
            - specific_rso_names: list of any specific RSOs mentioned
            - clarification_needed: boolean
            - follow_up_question: string if clarification needed"""

            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "user", "content": intent_prompt}
                ],
                model="mixtral-8x7b-32768",
                temperature=0.3
            )

            intent_analysis = json.loads(response.choices[0].message.content)
            logger.info(f"Query intent analysis: {intent_analysis}")
            return intent_analysis

        except Exception as e:
            logger.error(f"Error in analyze_query_intent: {str(e)}", exc_info=True)
            return None

    def get_relevant_rsos(self, query, top_k=5):
        """Get relevant RSOs based on query"""
        try:
            start_time = time.time()
            logger.info(f"Getting relevant RSOs for query: {query}")
            
            query_embedding = self.embed_model.encode(query).tolist()
            logger.info("Query embedding created")
            
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            query_time = time.time() - start_time
            logger.info(f"Found {len(results.matches)} matching RSOs in {query_time:.2f} seconds")
            
            return results.matches
        except Exception as e:
            logger.error(f"Error in get_relevant_rsos: {str(e)}", exc_info=True)
            raise

    def get_specific_rso_info(self, rso_name):
        """Get detailed information about a specific RSO"""
        try:
            # Encode the RSO name and search
            query_embedding = self.embed_model.encode(rso_name).tolist()
            results = self.index.query(
                vector=query_embedding,
                top_k=3,
                include_metadata=True
            )
            
            # Return the best match if score is high enough
            if results.matches and results.matches[0].score > 0.8:
                return results.matches[0].metadata
            return None
        except Exception as e:
            logger.error(f"Error in get_specific_rso_info: {str(e)}", exc_info=True)
            return None

    def format_context(self, relevant_rsos):
        """Format RSO information into readable context"""
        logger.info("Formatting RSO context")
        try:
            if not relevant_rsos:
                return "No RSOs found that match the query."
            
            context = "Here are the relevant RSOs:\n\n"
            
            for rso in relevant_rsos:
                metadata = rso.metadata
                context += f"Name: {metadata.get('name', 'N/A')}\n"
                context += f"Description: {metadata.get('description', 'N/A')}\n"
                context += f"Categories: {', '.join(metadata.get('categories', []))}\n"
                contact = metadata.get('contact_email', 'N/A')
                context += f"Contact: {contact}\n"
                if metadata.get('social_media_links'):
                    context += f"Social Media: {', '.join(metadata['social_media_links'])}\n"
                if metadata.get('meeting_times'):
                    context += f"Meeting Times: {metadata['meeting_times']}\n"
                if metadata.get('additional_info'):
                    context += f"Additional Info: {metadata['additional_info']}\n"
                context += f"Website: {metadata.get('full_url', 'N/A')}\n\n"
            
            return context
            
        except Exception as e:
            logger.error(f"Error in format_context: {str(e)}")
            raise

    def generate_response(self, query):
        """Generate a response based on the query"""
        try:
            start_time = time.time()
            logger.info(f"Generating response for query: {query}")
            
            # First, analyze the query intent
            intent = self.analyze_query_intent(query)
            if not intent:
                return "I'm having trouble understanding your question. Could you please rephrase it?"
            
            context = ""
            if intent.get('needs_rso_lookup'):
                # Get RSO information based on search terms
                search_terms = " ".join(intent.get('search_terms', []))
                relevant_rsos = self.get_relevant_rsos(search_terms or query)
                context += self.format_context(relevant_rsos)
            
            # For specific RSO questions, get detailed info
            if intent.get('specific_rso_names'):
                for rso_name in intent['specific_rso_names']:
                    rso_info = self.get_specific_rso_info(rso_name)
                    if rso_info:
                        context += f"\nDetailed information for {rso_name}:\n"
                        for key, value in rso_info.items():
                            if value:  # Only include non-empty fields
                                context += f"{key}: {value}\n"
                        context += "\n"

            # Construct the appropriate prompt based on query type
            if intent.get('query_type') == 'specific_info':
                prompt = f"""The student is asking for specific information: "{query}"
                Here's the RSO information we have:
                {context}
                Please answer their specific question directly."""

            elif intent.get('query_type') == 'comparison':
                prompt = f"""The student wants to compare RSOs: "{query}"
                Here's the information about the relevant RSOs:
                {context}
                Please compare these RSOs, highlighting key differences and similarities."""

            elif intent.get('query_type') == 'recommendation':
                prompt = f"""The student is looking for RSO recommendations based on: "{query}"
                Here are potentially relevant RSOs:
                {context}
                Please provide personalized recommendations based on their interests."""

            else:
                prompt = f"""The student asks: "{query}"
                Here's relevant RSO information:
                {context}
                Please provide a helpful response that directly addresses their question."""

            # Add clarification if needed
            if intent.get('clarification_needed'):
                prompt += f"\nAlso, kindly ask this follow-up question: {intent['follow_up_question']}"

            logger.info("Sending request to Groq")
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model="mixtral-8x7b-32768",
                temperature=0.7,
                max_tokens=1024
            )
            
            total_time = time.time() - start_time
            logger.info(f"Response generated in {total_time:.2f} seconds")
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in generate_response: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"

def get_bot_instance():
    """Get or create a singleton instance of RSORagBot"""
    global _bot_instance
    if _bot_instance is None:
        logger.info("Creating new RSORagBot instance")
        _bot_instance = RSORagBot()
    return _bot_instance

def main():
    """Main function to handle command line queries"""
    logger.info("Starting RSO bot main function")
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