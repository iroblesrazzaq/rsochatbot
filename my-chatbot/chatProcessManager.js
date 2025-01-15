// chatProcessManager.js
import { PythonShell } from 'python-shell';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import { createRequire } from 'module';

// Initialize dotenv
dotenv.config();

// Set up __dirname equivalent for ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Create require function
const require = createRequire(import.meta.url);

class ChatProcessManager {
    constructor() {
        this.processes = new Map();
        this.processTimeout = 30 * 60 * 1000; // 30 minutes
        this.maxProcesses = 10;
        this.startCleanupInterval();
    }

    async getChatProcess(chatId) {
        try {
            // Check existing process
            const existingProcess = this.processes.get(chatId);
            if (existingProcess && existingProcess.process) {
                existingProcess.lastUsed = Date.now();
                return existingProcess.process;
            }

            // Check process limit
            if (this.processes.size >= this.maxProcesses) {
                throw new Error('Maximum number of chat processes reached');
            }

            // Set up Python process
            const scriptPath = path.join(__dirname, 'scripts', 'persistent_bot.py');
            const env = {
                ...process.env,
                PYTHONUNBUFFERED: '1',
                TOKENIZERS_PARALLELISM: 'false',
                CHAT_ID: chatId
            };

            // Configure PythonShell options
            const options = {
                mode: 'json',
                pythonPath: 'python3',
                pythonOptions: ['-u'],
                scriptPath: path.dirname(scriptPath),
                env: env
            };

            // Create and initialize process
            const pythonProcess = new PythonShell(path.basename(scriptPath), options);
            
            // Wait for process initialization
            await new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Process initialization timeout'));
                }, 30000);

                pythonProcess.once('message', (message) => {
                    if (message && message.status === 'ready') {
                        clearTimeout(timeout);
                        resolve();
                    }
                });

                pythonProcess.once('error', (err) => {
                    clearTimeout(timeout);
                    reject(err);
                });
            });

            // Store process
            this.processes.set(chatId, {
                process: pythonProcess,
                lastUsed: Date.now()
            });

            return pythonProcess;

        } catch (err) {
            console.error(`Error creating process for chat ${chatId}:`, err);
            throw err;
        }
    }

    async sendMessage(chatId, message) {
        try {
            const pythonProcess = await this.getChatProcess(chatId);
            
            return new Promise((resolve, reject) => {
                const timeoutId = setTimeout(() => {
                    reject(new Error('Request timed out after 60 seconds'));
                }, 60000);

                const outputBuffer = [];
                let errorOccurred = false;

                const messageHandler = (response) => {
                    console.log('Received message from Python:', response);
                    if (response && (response.response || response.error)) {
                        clearTimeout(timeoutId);
                        if (response.error) {
                            reject(new Error(response.error));
                        } else {
                            resolve(response.response);
                        }
                    } else {
                        outputBuffer.push(response);
                    }
                };

                const errorHandler = (stderr) => {
                    // Log all stderr for debugging
                    console.log('Python stderr:', stderr);
                    // Only treat non-progress messages as errors
                    if (!stderr.includes('Batches:') && 
                        !stderr.includes('it/s]') && 
                        !stderr.includes('INFO')) {
                        console.error('Python error:', stderr);
                        errorOccurred = true;
                    }
                };

                const endHandler = (err, code, signal) => {
                    console.log('Python process ended:', { err, code, signal });
                    clearTimeout(timeoutId);
                    pythonProcess.removeListener('message', messageHandler);
                    pythonProcess.removeListener('stderr', errorHandler);

                    if (err || errorOccurred) {
                        console.error('Python script error:', { err, code, signal });
                        reject(err || new Error('Python script failed'));
                        return;
                    }

                    try {
                        // If we haven't resolved yet, try to use the buffer
                        const lastOutput = outputBuffer[outputBuffer.length - 1];
                        if (lastOutput) {
                            const result = typeof lastOutput === 'string' ? 
                                JSON.parse(lastOutput) : lastOutput;
                            
                            if (result.error) {
                                reject(new Error(result.error));
                            } else if (result.response) {
                                resolve(result.response);
                            } else {
                                reject(new Error('No valid response in output'));
                            }
                        } else {
                            reject(new Error('No output received from Python process'));
                        }
                    } catch (e) {
                        console.error('Error processing Python output:', e);
                        reject(new Error('Invalid response format from Python script'));
                    }
                };

                pythonProcess.on('message', messageHandler);
                pythonProcess.on('stderr', errorHandler);
                pythonProcess.on('error', (err) => {
                    errorOccurred = true;
                    console.error('Process error:', err);
                });
                pythonProcess.on('end', endHandler);

                try {
                    pythonProcess.send(message);
                } catch (err) {
                    clearTimeout(timeoutId);
                    reject(new Error('Failed to send message to Python process: ' + err.message));
                }
            });
        } catch (err) {
            throw new Error('Failed to get Python process: ' + err.message);
        }
    }

    startCleanupInterval() {
        setInterval(() => {
            const now = Date.now();
            for (const [chatId, {process, lastUsed}] of this.processes.entries()) {
                if (now - lastUsed > this.processTimeout) {
                    process.end();
                    this.processes.delete(chatId);
                    console.log(`Cleaned up inactive process for chat ${chatId}`);
                }
            }
        }, 5 * 60 * 1000);
    }

    async cleanup() {
        for (const [chatId, {process}] of this.processes.entries()) {
            process.end();
            this.processes.delete(chatId);
        }
    }
}

// Export singleton instance
export default new ChatProcessManager();