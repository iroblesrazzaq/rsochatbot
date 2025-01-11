import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const ChatInterface = () => {
  const [chats, setChats] = useState([]);
  const [currentChat, setCurrentChat] = useState(null);
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [backendUrl, setBackendUrl] = useState(null);
  const [connectionError, setConnectionError] = useState(false);
  const [discoveryAttempts, setDiscoveryAttempts] = useState(0);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentChat?.messages]);

  useEffect(() => {
    const discoverBackendPort = async () => {
      try {
        const startPort = 3003;
        const maxPort = startPort + 20;
        let connected = false;

        console.log('Starting backend discovery...');

        for (let port = startPort; port <= maxPort; port++) {
          try {
            console.log(`Trying port ${port}...`);
            const response = await axios.get(`http://localhost:${port}/api/port`, {
              headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
              },
              withCredentials: true,
              timeout: 1000 // 1 second timeout for each attempt
            });

            if (response.data && response.data.port) {
              const url = `http://localhost:${response.data.port}`;
              console.log(`Successfully connected to backend at ${url}`);
              setBackendUrl(url);
              setConnectionError(false);
              connected = true;
              break;
            }
          } catch (e) {
            console.log(`Port ${port} not available:`, e.message);
          }
        }

        if (!connected) {
          console.error('Could not connect to any backend port');
          setConnectionError(true);
          if (discoveryAttempts < 3) {
            setTimeout(() => {
              setDiscoveryAttempts(prev => prev + 1);
            }, 2000);
          }
        }
      } catch (error) {
        console.error('Backend discovery failed:', error);
        setConnectionError(true);
        if (discoveryAttempts < 3) {
          setTimeout(() => {
            setDiscoveryAttempts(prev => prev + 1);
          }, 2000);
        }
      }
    };

    discoverBackendPort();
  }, [discoveryAttempts]);

  const createChat = () => {
    const newChat = {
      id: Date.now(),
      title: `Chat ${chats.length + 1}`,
      messages: []
    };
    setChats(prevChats => [...prevChats, newChat]);
    setCurrentChat(newChat);
    console.log('Created new chat:', newChat);
  };

  const deleteChat = (chatId) => {
    setChats(prevChats => prevChats.filter(chat => chat.id !== chatId));
    if (currentChat?.id === chatId) {
      setCurrentChat(null);
    }
    console.log('Deleted chat:', chatId);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    console.log('Send attempt:', {
      hasMessage: Boolean(message.trim()),
      hasCurrentChat: Boolean(currentChat),
      hasBackendUrl: Boolean(backendUrl),
      message,
      currentChatId: currentChat?.id
    });

    if (!message.trim() || !currentChat || !backendUrl) {
      console.log('Send conditions not met');
      return;
    }

    const updatedChat = {
      ...currentChat,
      messages: [...currentChat.messages, { role: 'user', content: message }]
    };
    
    setChats(prevChats => 
      prevChats.map(chat => chat.id === currentChat.id ? updatedChat : chat)
    );
    setCurrentChat(updatedChat);
    
    const userMessage = message;
    setMessage('');
    setIsLoading(true);

    try {
      console.log('Sending message to:', `${backendUrl}/api/chat`);
      
      const response = await axios.post(`${backendUrl}/api/chat`, 
        {
          message: userMessage,
          chatId: currentChat.id
        }, 
        {
          headers: {
            'Content-Type': 'application/json'
          },
          withCredentials: true
        }
      );

      console.log('Received response:', response.data);

      if (response.data && response.data.response) {
        const updatedChatWithResponse = {
          ...updatedChat,
          messages: [...updatedChat.messages, { 
            role: 'assistant', 
            content: response.data.response 
          }]
        };
        setChats(prevChats => 
          prevChats.map(chat => chat.id === currentChat.id ? updatedChatWithResponse : chat)
        );
        setCurrentChat(updatedChatWithResponse);
      } else {
        throw new Error('Invalid response format from server');
      }
    } catch (error) {
      console.error('Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      });

      const errorMessage = error.response?.data?.error || error.message || 'Failed to send message';
      const updatedChatWithError = {
        ...updatedChat,
        messages: [...updatedChat.messages, 
          { role: 'system', content: `Error: ${errorMessage}`, isError: true }
        ]
      };
      setChats(prevChats => 
        prevChats.map(chat => chat.id === currentChat.id ? updatedChatWithError : chat)
      );
      setCurrentChat(updatedChatWithError);
    } finally {
      setIsLoading(false);
    }
  };

  if (connectionError) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-100">
        <div className="text-center p-4 bg-white rounded shadow">
          <h2 className="text-xl text-red-600 mb-2">Connection Error</h2>
          <p className="mb-2">Unable to connect to the backend server.</p>
          <p className="text-sm text-gray-600 mb-4">
            Make sure the backend server is running and try again.
          </p>
          <button 
            onClick={() => setDiscoveryAttempts(prev => prev + 1)} 
            className="mt-4 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            Retry Connection ({3 - discoveryAttempts} attempts remaining)
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Debug info */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed top-0 right-0 bg-black text-white p-2 text-xs">
          Backend: {backendUrl || 'Not connected'}
        </div>
      )}

      {/* Sidebar */}
      <div className="w-64 bg-white p-4 border-r">
        <button
          onClick={createChat}
          className="w-full bg-blue-500 text-white p-2 rounded mb-4 hover:bg-blue-600"
        >
          New Chat
        </button>
        <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-6rem)]">
          {chats.map(chat => (
            <div
              key={chat.id}
              className="flex justify-between items-center p-2 hover:bg-gray-100 rounded cursor-pointer"
              onClick={() => setCurrentChat(chat)}
            >
              <span className={`text-black ${currentChat?.id === chat.id ? 'font-bold' : ''}`}>
                {chat.title}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteChat(chat.id);
                }}
                className="text-red-500 hover:text-red-700"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        {currentChat ? (
          <>
            {/* Messages */}
            <div className="flex-1 p-4 overflow-y-auto bg-white">
              {currentChat.messages.map((msg, index) => (
                <div
                  key={index}
                  className={`mb-4 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}
                >
                  <div
                    className={`inline-block p-2 rounded-lg max-w-[70%] ${
                      msg.role === 'user'
                        ? 'bg-blue-500 text-white'
                        : msg.isError
                        ? 'bg-red-100 text-red-600'
                        : 'bg-gray-200 text-black'
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="text-center text-gray-500">
                  AI is thinking...
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t bg-white">
              <form onSubmit={handleSendMessage} className="flex space-x-4">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="flex-1 p-2 border rounded text-black"
                  placeholder="Type your message..."
                />
                <button
                  type="submit"
                  disabled={isLoading || !backendUrl || !currentChat}
                  className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:bg-blue-300"
                >
                  {isLoading ? 'Sending...' : 'Send'}
                </button>
              </form>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            Select or create a chat to start messaging
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;