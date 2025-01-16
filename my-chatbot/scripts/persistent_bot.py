#!/usr/bin/env python3
import sys
import json
import logging
import asyncio
from pathlib import Path
import os
from typing import Optional
from dotenv import load_dotenv
from chat_manager import get_chat_manager

# Configure logging with a detailed format for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class PersistentBot:
    def __init__(self):
        """
        Initialize the bot with necessary components and chat manager.
        Sets up environment and establishes connections for long-running chat sessions.
        """
        try:
            # Load environment variables from the correct path
            script_dir = Path(__file__).parent.absolute()
            env_path = script_dir.parent / '.env'
            load_dotenv(dotenv_path=env_path)
            
            # Get chat ID from environment
            self.chat_id = os.getenv('CHAT_ID')
            if not self.chat_id:
                raise ValueError("Chat ID not provided in environment variables")

            logger.info(f"Initializing persistent bot for chat {self.chat_id}")
            
            # Get the chat manager instance - this will initialize shared resources if needed
            self.chat_manager = get_chat_manager()
            
            # Initialize the chat instance for this session
            self.chat_manager.create_chat(self.chat_id)
            
            logger.info(f"Bot initialization complete for chat {self.chat_id}")
            
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}", exc_info=True)
            raise

    async def process_message(self, message: str) -> str:
        """
        Process a single message using the chat manager.
        
        Args:
            message: The input message to process
            
        Returns:
            The generated response string
        """
        try:
            # Process the message using the chat manager
            response = await self.chat_manager.process_message(self.chat_id, message)
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return f"Error processing message: {str(e)}"

    def cleanup(self):
        """
        Clean up resources for this chat session.
        Called when the bot is being shut down.
        """
        try:
            logger.info(f"Cleaning up resources for chat {self.chat_id}")
            self.chat_manager.cleanup_chat(self.chat_id)
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}", exc_info=True)

async def main():
    """
    Main function to handle the persistent bot lifecycle.
    Manages initialization, message processing loop, and cleanup.
    """
    try:
        # Initialize the bot
        bot = PersistentBot()
        logger.info("Bot ready to process messages")
        
        # Signal ready state to the parent process
        print(json.dumps({"status": "ready"}))
        sys.stdout.flush()

        # Process incoming messages in a loop
        for line in sys.stdin:
            try:
                # Parse the incoming message
                message = line.strip()
                if not message:
                    continue
                
                # Process the message
                response = await bot.process_message(message)
                
                # Send the response
                print(json.dumps({"response": response}))
                sys.stdout.flush()
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                print(json.dumps({"error": str(e)}))
                sys.stdout.flush()
                
    except Exception as e:
        logger.error(f"Fatal error in main loop: {str(e)}", exc_info=True)
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush()
    finally:
        # Ensure cleanup happens even if there's an error
        if 'bot' in locals():
            bot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())