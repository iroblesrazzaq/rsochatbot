#!/usr/bin/env python3
import logging
import threading
from typing import Dict, Optional
from chat_instance import ChatInstance
from shared_resources import SharedResources

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatManager:
    """
    Manages the lifecycle of chat instances and coordinates shared resources.
    Implements the singleton pattern to ensure only one manager exists.
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
        """Initialize the chat manager"""
        self.chats: Dict[str, ChatInstance] = {}
        self.chat_locks: Dict[str, threading.Lock] = {}
        self.shared_resources = SharedResources()  # Initialize shared resources
        logger.info("Chat manager initialized")

    def create_chat(self, chat_id: str) -> ChatInstance:
        """
        Create a new chat instance with the given ID.
        
        Args:
            chat_id: Unique identifier for the chat
            
        Returns:
            The created ChatInstance
            
        Raises:
            ValueError: If chat_id already exists
        """
        with self._lock:
            if chat_id in self.chats:
                raise ValueError(f"Chat {chat_id} already exists")
            
            logger.info(f"Creating new chat instance: {chat_id}")
            chat_instance = ChatInstance(chat_id)
            self.chats[chat_id] = chat_instance
            self.chat_locks[chat_id] = threading.Lock()
            return chat_instance

    def get_chat(self, chat_id: str) -> Optional[ChatInstance]:
        """
        Get an existing chat instance.
        
        Args:
            chat_id: ID of the chat to retrieve
            
        Returns:
            ChatInstance if found, None otherwise
        """
        return self.chats.get(chat_id)

    async def process_message(self, chat_id: str, message: str) -> str:
        """
        Process a message for a specific chat instance.
        Creates a new chat if it doesn't exist.
        
        Args:
            chat_id: ID of the chat
            message: Message to process
            
        Returns:
            Generated response
        """
        # Get or create chat instance
        chat = self.get_chat(chat_id)
        if not chat:
            chat = self.create_chat(chat_id)
        
        # Process message with thread safety for this chat
        with self.chat_locks[chat_id]:
            response = await chat.generate_response(message)
            return response

    def cleanup_chat(self, chat_id: str):
        """
        Clean up resources for a specific chat.
        
        Args:
            chat_id: ID of the chat to clean up
        """
        with self._lock:
            if chat_id in self.chats:
                logger.info(f"Cleaning up chat {chat_id}")
                self.chats[chat_id].cleanup()
                del self.chats[chat_id]
                del self.chat_locks[chat_id]

    def cleanup_all(self):
        """Clean up all chat instances and shared resources"""
        logger.info("Cleaning up all chats and resources")
        with self._lock:
            for chat_id in list(self.chats.keys()):
                self.cleanup_chat(chat_id)
            self.shared_resources.cleanup()

# Global instance
_chat_manager = None
_manager_lock = threading.Lock()

def get_chat_manager() -> ChatManager:
    """
    Get or create the global chat manager instance.
    
    Returns:
        The singleton ChatManager instance
    """
    global _chat_manager
    with _manager_lock:
        if _chat_manager is None:
            _chat_manager = ChatManager()
        return _chat_manager