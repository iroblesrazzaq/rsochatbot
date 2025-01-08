import React, { useState } from 'react';
import { Send, Plus, MessageSquare } from 'lucide-react';

const ChatInterface = () => {
  const [messages, setMessages] = useState([
    { id: 1, content: "How can I help you today?", role: "assistant" }
  ]);
  const [inputText, setInputText] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const chatHistory = [
    { id: 1, title: "Previous Chat 1" },
    { id: 2, title: "Previous Chat 2" },
    { id: 3, title: "Previous Chat 3" },
  ];

  const handleSend = () => {
    if (inputText.trim() === "") return;
    setMessages([...messages, 
      { id: messages.length + 1, content: inputText, role: "user" },
      { id: messages.length + 2, content: "This is a simulated response.", role: "assistant" }
    ]);
    setInputText("");
  };

  return (
    <div className="h-screen w-full flex bg-[#343541]">
      {/* Sidebar */}
      <div className={`${isSidebarOpen ? 'w-[260px]' : 'w-0'} h-full bg-[#1e1e1e] flex flex-col transition-all duration-300`}>
        {/* New Chat Button */}
        <div className="p-2">
          <button className="w-full flex items-center gap-3 rounded-md bg-[#2d2d2d] p-3 text-sm text-white hover:bg-[#343434] transition-colors duration-200">
            <Plus size={16} />
            New chat
          </button>
        </div>

        {/* Chat History */}
        <div className="flex-1 overflow-y-auto">
          {chatHistory.map(chat => (
            <div key={chat.id} className="flex items-center gap-3 px-3 py-3 hover:bg-[#2d2d2d] cursor-pointer group text-gray-300">
              <MessageSquare size={16} className="shrink-0" />
              <span className="text-sm truncate">{chat.title}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative">
        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto">
          {messages.map((message) => (
            <div key={message.id} className="p-4 flex justify-center items-start">
              <div className="flex max-w-3xl w-full gap-4">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                  message.role === "assistant" ? "bg-blue-500" : "bg-gray-500"
                }`}>
                  {message.role === "assistant" ? (
                    <MessageSquare size={16} className="text-white" />
                  ) : "U"}
                </div>
                <div className="flex-1 space-y-2 overflow-hidden">
                  <p className="text-gray-100">{message.content}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-800 bg-[#343541] p-4">
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
              placeholder="Type a message..."
              className="w-full resize-none rounded-lg border border-gray-700 bg-[#40414f] p-4 pr-12 text-white focus:outline-none focus:border-gray-600"
              style={{ height: '56px', maxHeight: '200px', overflowY: 'hidden' }}
              rows="1"
            />
            <button
              onClick={handleSend}
              disabled={!inputText.trim()}
              className="absolute right-3 bottom-3 p-1.5 rounded text-gray-400 hover:text-white disabled:hover:text-gray-400 disabled:opacity-40"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;