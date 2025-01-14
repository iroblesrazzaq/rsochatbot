// api/chat.js
import { PythonShell } from 'python-shell';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Reduced timeout since we've optimized the Python script
const TIMEOUT = 30000; // 30 seconds timeout

// Cache for script path verification
let scriptPathVerified = false;

const verifyScriptPath = async (scriptPath) => {
    if (scriptPathVerified) return;
    
    try {
        await import('fs').then(fs => fs.promises.access(scriptPath));
        scriptPathVerified = true;
    } catch (error) {
        throw new Error('Python script not found at ' + scriptPath);
    }
};

const chatHandler = async (req) => {
    console.log('\n========== CHAT REQUEST STARTED ==========');
    const startTime = Date.now();
    
    try {
        if (!req.message) {
            throw new Error('Message is required');
        }

        const scriptPath = path.join(__dirname, '..', 'scripts', 'openai_bot.py');
        await verifyScriptPath(scriptPath);
        
        const options = {
            mode: 'json',
            pythonPath: 'python3',
            pythonOptions: ['-u'],
            scriptPath: path.dirname(scriptPath),
            args: [req.message],
            env: {
                ...process.env,
                PYTHONUNBUFFERED: '1'
            }
        };

        const response = await new Promise((resolve, reject) => {
            const timeoutId = setTimeout(() => {
                reject(new Error(`Request timed out after ${TIMEOUT/1000} seconds`));
            }, TIMEOUT);

            let outputBuffer = [];
            const pyshell = new PythonShell(path.basename(scriptPath), options);

            pyshell.on('message', (message) => outputBuffer.push(message));
            pyshell.on('stderr', (stderr) => console.error('Python stderr:', stderr));

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