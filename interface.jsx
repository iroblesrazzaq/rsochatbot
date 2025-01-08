import React, { useState } from 'react';
import { Send, Menu, Plus, User, MessageSquare } from 'lucide-react';

const ChatGPTInterface = () => {
  // State for managing messages and input
  const [messages, setMessages] = useState([
    { id: 1, content: "Hello! How can I help you today?", role: "assistant" }
  ]);
  const [inputText, setInputText] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Simulated chat history for the sidebar
  const chatHistory = [
    { id: 1, title: "Previous Chat 1" },
    { id: 2, title: "Previous Chat 2" },
    { id: 3, title: "Previous Chat 3" },
  ];

  // Handler for sending messages
  const handleSend = () => {
    if (inputText.trim() === "") return;
    setMessages([...messages, 
      { id: messages.length + 1, content: inputText, role: "user" },
      { id: messages.length + 2, content: "This is a simulated response.", role: "assistant" }
    ]);
    setInputText("");
  };

  return (
    // Main container with dark theme
    <div className="h-screen w-full bg-gray-800 flex">
      {/* Sidebar - ChatGPT style navigation */}
      <div className={`${isSidebarOpen ? 'w-64' : 'w-0'} bg-gray-900 transition-all duration-300 overflow-hidden flex flex-col`}>
        {/* New Chat Button */}
        <button className="flex items-center gap-2 p-4 text-white border border-gray-700 rounded-md m-2 hover:bg-gray-800">
          <Plus size={16} />
          New chat
        </button>

        {/* Previous Chats List */}
        <div className="flex-1 overflow-y-auto">
          {chatHistory.map(chat => (
            <div key={chat.id} className="flex items-center gap-2 p-3 text-gray-300 hover:bg-gray-800 cursor-pointer">
              <MessageSquare size={16} />
              <span className="truncate">{chat.title}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col relative">
        {/* Top Navigation Bar */}
        <div className="h-12 border-b border-gray-700 flex items-center px-4">
          <button 
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="text-gray-400 hover:text-white"
          >
            <Menu size={24} />
          </button>
        </div>

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`py-8 ${
                message.role === "assistant" ? "bg-gray-800" : "bg-gray-700"
              }`}
            >
              <div className="max-w-3xl mx-auto flex gap-6 px-4">
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-sm flex items-center justify-center ${
                  message.role === "assistant" ? "bg-green-600" : "bg-blue-600"
                }`}>
                  {message.role === "assistant" ? (
                    "AI"
                  ) : (
                    <User size={20} />
                  )}
                </div>
                
                {/* Message Content */}
                <div className="flex-1 text-gray-100">
                  {message.content}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Input Container */}
        <div className="border-t border-gray-700 p-4">
          <div className="max-w-3xl mx-auto relative">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Send a message..."
              className="w-full bg-gray-700 text-white rounded-lg pl-4 pr-12 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              rows="1"
              style={{ minHeight: '44px', maxHeight: '200px' }}
            />
            
            {/* Send Button */}
            <button
              onClick={handleSend}
              disabled={!inputText.trim()}
              className="absolute right-2 bottom-1.5 p-1.5 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatGPTInterface;