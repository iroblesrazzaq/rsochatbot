// api/chat.js
import { PythonShell } from 'python-shell';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TIMEOUT = 60000; // Increased to 60 seconds

const chatHandler = async (req) => {
    console.log('\n========== CHAT REQUEST STARTED ==========');
    console.log('Timestamp:', new Date().toISOString());
    console.log('Request payload:', req);
    
    try {
        if (!req.message) {
            console.log('Error: Message is missing from request');
            throw new Error('Message is required');
        }

        const scriptPath = path.join(__dirname, '..', 'scripts', 'rso_bot.py');
        console.log('Python script path:', scriptPath);
        
        // Check if the script exists
        try {
            await import('fs').then(fs => fs.promises.access(scriptPath));
            console.log('Python script found at path');
        } catch (error) {
            console.error('Python script not found:', error);
            throw new Error('Python script not found at ' + scriptPath);
        }
        
        const options = {
            mode: 'json',
            pythonPath: 'python3',
            pythonOptions: ['-u'], // unbuffered output
            scriptPath: path.dirname(scriptPath),
            args: [req.message],
            env: {
                ...process.env,
                PYTHONUNBUFFERED: '1'
            }
        };

        console.log('Starting Python script with options:', {
            scriptPath: options.scriptPath,
            pythonPath: options.pythonPath,
            message: req.message
        });

        const runPythonScript = () => {
            console.log('Executing Python script...');
            return new Promise((resolve, reject) => {
                let hasResponded = false;
                let outputBuffer = [];
                
                const timeoutId = setTimeout(() => {
                    if (!hasResponded) {
                        hasResponded = true;
                        console.error('Python script execution timed out');
                        console.error('Collected output:', outputBuffer.join('\n'));
                        reject(new Error(`Python script execution timed out after ${TIMEOUT/1000} seconds`));
                    }
                }, TIMEOUT);

                const pyshell = new PythonShell(path.basename(scriptPath), options);

                pyshell.on('message', (message) => {
                    console.log('Python output:', message);
                    outputBuffer.push(message);
                });

                pyshell.on('stderr', (stderr) => {
                    console.error('Python stderr:', stderr);
                    outputBuffer.push(`ERROR: ${stderr}`);
                });

                pyshell.end((err, code, signal) => {
                    clearTimeout(timeoutId);

                    if (hasResponded) return;
                    hasResponded = true;

                    if (err) {
                        console.error('Python script error:', err);
                        console.error('Exit code:', code);
                        console.error('Signal:', signal);
                        console.error('Collected output:', outputBuffer.join('\n'));
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
        };

        console.log('Awaiting Python script execution...');
        const response = await runPythonScript();
        console.log('Python script execution completed successfully');
        console.log('Response:', response);
        console.log('========== CHAT REQUEST COMPLETED ==========\n');
        return { response };
        
    } catch (error) {
        console.error('========== CHAT REQUEST FAILED ==========');
        console.error('Error details:', error);
        console.error('Stack trace:', error.stack);
        console.error('==========================================\n');
        throw error;
    }
};

export default chatHandler;