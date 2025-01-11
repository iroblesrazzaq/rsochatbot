// api/chat.js
const chatHandler = async (req) => {
    console.log('Chat handler received request:', req);
    
    // Simple echo response for testing
    return {
        response: `Received your message: ${req.message}`
    };
};

export default chatHandler;