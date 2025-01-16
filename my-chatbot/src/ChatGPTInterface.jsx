import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

const LoadingSpinner = () => {
  return (
    <div className="flex items-center justify-center p-4">
      <div className="relative w-8 h-8">
        <div className="absolute border-4 border-gray-200 rounded-full w-full h-full"></div>
        <div 
          className="absolute border-4 border-maroon rounded-full w-full h-full animate-spin" 
          style={{ borderTopColor: 'transparent' }}
        ></div>
      </div>
    </div>
  );
};

// Message content component for handling markdown and formatting
const MessageContent = ({ content, role }) => {
  if (role === 'user') {
    return <div className="whitespace-pre-wrap">{content}</div>;
  }

  // Try to parse JSON content if it's a string
  let messageContent = content;
  try {
    const parsed = JSON.parse(content);
    if (parsed.data && parsed.data.content) {
      messageContent = parsed.data.content;
    } else if (parsed.response) {
      try {
        const nestedResponse = JSON.parse(parsed.response);
        if (nestedResponse.data && nestedResponse.data.content) {
          messageContent = nestedResponse.data.content;
        } else {
          messageContent = parsed.response;
        }
      } catch {
        messageContent = parsed.response;
      }
    }
  } catch {
    // If parsing fails, use the original content
    messageContent = content;
  }

  return (
    <ReactMarkdown
      className="text-left break-words"
      components={{
        p: ({ children }) => <p className="mb-2">{children}</p>,
        h1: ({ children }) => <h1 className="text-xl font-bold mb-2 mt-3">{children}</h1>,
        h2: ({ children }) => <h2 className="text-lg font-bold mb-2 mt-3">{children}</h2>,
        h3: ({ children }) => <h3 className="text-md font-bold mb-2 mt-3">{children}</h3>,
        ul: ({ children }) => <ul className="list-disc ml-4 mb-2">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal ml-4 mb-2">{children}</ol>,
        li: ({ children }) => <li className="mb-1">{children}</li>,
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          return !inline && match ? (
            <div className="my-2">
              <SyntaxHighlighter
                style={tomorrow}
                language={match[1]}
                PreTag="div"
                className="rounded"
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            </div>
          ) : (
            <code className="bg-gray-100 px-1 rounded" {...props}>
              {children}
            </code>
          );
        },
      }}
    >
      {messageContent}
    </ReactMarkdown>
  );
};

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
            const response = await axios.get(`http://localhost:${port}/api/port`, {
              headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
              },
              withCredentials: true,
              timeout: 1000
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

  useEffect(() => {
    const initializeFirstChat = async () => {
      if (chats.length === 0 && backendUrl) {
        try {
          const initialChatId = Date.now();
          setIsLoading(true);

          const initialChat = {
            id: initialChatId,
            title: "Welcome Chat",
            messages: [{
              role: 'assistant',
              content: `Hi! I'm your UChicago RSO assistant. Ask me about anything related to UChicago RSOs!`
            }]
          };
          setChats([initialChat]);
          setCurrentChat(initialChat);

          await axios.post(`${backendUrl}/api/chat/init`, 
            { chatId: initialChatId.toString() },
            { withCredentials: true }
          );
          
          console.log('Initial chat bot initialized successfully');
          
        } catch (error) {
          console.error('Error initializing first chat:', error);
          const errorChat = {
            id: Date.now(),
            title: "Welcome Chat",
            messages: [
              {
                role: 'assistant',
                content: `Hi! I'm your UChicago RSO assistant. Ask me about anything related to UChicago RSOs!`
              },
              {
                role: 'system',
                content: 'Error initializing chat. Some features may be unavailable.',
                isError: true
              }
            ]
          };
          setChats([errorChat]);
          setCurrentChat(errorChat);
        } finally {
          setIsLoading(false);
        }
      }
    };

    initializeFirstChat();
  }, [backendUrl, chats.length]);

  const createChat = async () => {
    try {
      const newChatId = Date.now();
      setIsLoading(true);

      await axios.post(`${backendUrl}/api/chat/init`, 
        { chatId: newChatId.toString() },
        { withCredentials: true }
      );

      const newChat = {
        id: newChatId,
        title: `Chat ${chats.length + 1}`,
        messages: []
      };

      setChats(prevChats => [...prevChats, newChat]);
      setCurrentChat(newChat);
      console.log('Created new chat:', newChat);
      
    } catch (error) {
      console.error('Error creating chat:', error);
    } finally {
      setIsLoading(false);
    }
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
    
    if (!message.trim() || !currentChat || !backendUrl) {
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
      const response = await axios.post(`${backendUrl}/api/chat`, 
        {
          message: userMessage,
          chatId: currentChat.id.toString()
        }, 
        {
          headers: {
            'Content-Type': 'application/json'
          },
          withCredentials: true
        }
      );
  
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
      }
    } catch (error) {
      console.error('Error details:', error);
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
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed top-0 right-0 bg-black text-white p-2 text-xs">
          Backend: {backendUrl || 'Not connected'}
        </div>
      )}

      {/* Sidebar */}
      <div className="w-64 bg-maroon p-4 border-r">
        <button
          onClick={createChat}
          className="w-full bg-white text-maroon-dark p-2 rounded mb-4 border-2 border-transparent font-normal hover:border-maroon hover:font-bold"
        >
          New Chat
        </button>
        <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-6rem)]">
          {chats.map(chat => (
            <div
              key={chat.id}
              className="flex justify-between bg-maroon-dark items-center rounded p-2 border-2 border-transparent cursor-pointer hover:border-white"
              onClick={() => setCurrentChat(chat)}
            >
              <span className={`text-white ${currentChat?.id === chat.id ? 'font-bold' : ''}`}>
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
                    className={`inline-block p-3 rounded-lg ${
                      msg.role === 'user' ? 'max-w-[70%]' : 'max-w-[85%]'
                    } ${
                      msg.role === 'user'
                        ? 'bg-maroon text-white'
                        : msg.isError
                        ? 'bg-red-100 text-red-600'
                        : 'bg-gray-200 text-black'
                    }`}
                  >
                    <MessageContent 
                      content={msg.content} 
                      role={msg.role}
                    />
                  </div>
                </div>
              ))}
              {isLoading && <LoadingSpinner />}
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
                  className="bg-maroon text-white px-4 py-2 rounded font-normal hover:font-bold disabled:opacity-50"
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