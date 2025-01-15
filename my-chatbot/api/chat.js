// api/chat.js
import chatProcessManager from '../chatProcessManager.js';

const chatHandler = async (req) => {
    console.log('\n========== CHAT REQUEST STARTED ==========');
    const startTime = Date.now();
    
    try {
        if (!req.message) {
            throw new Error('Message is required');
        }
        if (!req.chatId) {
            throw new Error('Chat ID is required');
        }

        // Use the process manager to send the message
        const response = await chatProcessManager.sendMessage(req.chatId, req.message);
        
        const executionTime = Date.now() - startTime;
        console.log(`Request completed in ${executionTime}ms`);
        console.log('========== CHAT REQUEST COMPLETED ==========\n');
        
        return { response };
        
    } catch (error) {
        console.error('========== CHAT REQUEST FAILED ==========');
        console.error('Error details:', error);
        throw error;
    }
};

export default chatHandler;