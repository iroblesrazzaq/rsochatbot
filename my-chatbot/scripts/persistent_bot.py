#!/usr/bin/env python3
import sys
import json
import logging
from pathlib import Path
import os
import asyncio
from typing import Optional
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class PersistentBot:
    def __init__(self):
        """Initialize the bot with all necessary components"""
        try:
            # Load environment variables
            script_dir = Path(__file__).parent.absolute()
            env_path = script_dir.parent / '.env'
            load_dotenv(dotenv_path=env_path)
            
            # Get chat ID from environment
            self.chat_id = os.getenv('CHAT_ID')
            if not self.chat_id:
                raise ValueError("Chat ID not provided")

            logger.info(f"Initializing bot for chat {self.chat_id}")
            
            # Initialize the actual bot (reuse your existing HybridRsoBot code)
            self.bot = self.initialize_bot()
            
            logger.info(f"Bot initialization complete for chat {self.chat_id}")
            
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}", exc_info=True)
            raise

    def initialize_bot(self):
        """Initialize the actual bot implementation"""
        # Import here to avoid circular imports
        from openai_bot import HybridRsoBot
        return HybridRsoBot()

    async def process_message(self, message: str) -> str:
        """Process a single message using the bot"""
        try:
            response = await self.bot.generate_response(message)
            return response
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            raise

async def main():
    """Main loop to handle incoming messages"""
    try:
        # Initialize the bot
        bot = PersistentBot()
        logger.info("Bot ready to process messages")
        
        print(json.dumps({"status": "ready"}))
        sys.stdout.flush()

        # Process incoming messages
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

if __name__ == "__main__":
    asyncio.run(main())