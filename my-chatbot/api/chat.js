// api/chat.js
import { PythonShell } from 'python-shell';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Increased timeout for initial model loading
const TIMEOUT = 60000; // 60 seconds timeout

const chatHandler = async (req) => {
    console.log('\n========== CHAT REQUEST STARTED ==========');
    const startTime = Date.now();
    
    try {
        if (!req.message) {
            throw new Error('Message is required');
        }

        const scriptPath = path.join(__dirname, '..', 'scripts', 'openai_bot.py');
        
        const options = {
            mode: 'json',
            pythonPath: 'python3',
            pythonOptions: ['-u'],
            scriptPath: path.dirname(scriptPath),
            args: [req.message],
            env: {
                ...process.env,
                PYTHONUNBUFFERED: '1',
                TOKENIZERS_PARALLELISM: 'false'
            }
        };

        const response = await new Promise((resolve, reject) => {
            const timeoutId = setTimeout(() => {
                reject(new Error(`Request timed out after ${TIMEOUT/1000} seconds`));
            }, TIMEOUT);

            const pyshell = new PythonShell(path.basename(scriptPath), options);
            let outputBuffer = [];

            pyshell.on('message', (message) => outputBuffer.push(message));
            
            pyshell.on('stderr', (stderr) => {
                // Only log non-progress bar output
                if (!stderr.includes('Batches:') && !stderr.includes('it/s]')) {
                    console.error('Python stderr:', stderr);
                }
            });

            pyshell.end((err, code, signal) => {
                clearTimeout(timeoutId);
                
                if (err) {
                    console.error('Python script error:', { err, code, signal });
                    reject(err);
                    return;
                }

                const lastOutput = outputBuffer[outputBuffer.length - 1];
                try {
                    const result = typeof lastOutput === 'string' ? JSON.parse(lastOutput) : lastOutput;
                    if (result.error) {
                        reject(new Error(result.error));
                    } else {
                        resolve(result.response);
                    }
                } catch (e) {
                    reject(new Error('Invalid response format from Python script'));
                }
            });
        });

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