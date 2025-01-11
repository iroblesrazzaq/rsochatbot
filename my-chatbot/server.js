import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import net from 'net';
import chatHandler from './api/chat.js';

dotenv.config();

const app = express();

const isPortAvailable = (port) => {
  return new Promise((resolve) => {
    const server = net.createServer()
      .once('error', () => {
        resolve(false);
      })
      .once('listening', () => {
        server.close();
        resolve(true);
      })
      .listen(port);
  });
};

const findAvailablePort = async (startPort) => {
  let port = startPort;
  while (!(await isPortAvailable(port))) {
    console.log(`Port ${port} is in use, trying next port...`);
    port++;
  }
  return port;
};

// Updated CORS configuration
app.use(cors({
  origin: ['http://localhost:5173', 'http://127.0.0.1:5173'],
  credentials: true,
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

// Add OPTIONS handling for preflight requests
app.options('*', cors());

app.use(express.json());

// Enhanced logging middleware
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
  console.log('Request headers:', req.headers);
  if (req.body && Object.keys(req.body).length > 0) {
    console.log('Request body:', req.body);
  }
  next();
});

// Enhanced port discovery endpoint
app.get('/api/port', (req, res) => {
  const port = app.get('port');
  console.log('Port discovery request received. Port:', port);
  console.log('Request origin:', req.headers.origin);
  res.json({ port: port, status: 'active' });
});

app.post('/api/chat', async (req, res) => {
  console.log('Received chat request:', req.body);
  try {
    if (!req.body.message) {
      throw new Error('Message is required');
    }
    
    const result = await chatHandler(req.body);
    console.log('Sending response:', result);
    res.json(result);
  } catch (error) {
    console.error('Error in chat endpoint:', error);
    res.status(500).json({ error: error.message });
  }
});

const startServer = async () => {
  const preferredPort = 3003;
  try {
    const port = await findAvailablePort(preferredPort);
    app.set('port', port);
    
    app.listen(port, () => {
      console.log(`Server running on http://localhost:${port}`);
      console.log('Available endpoints:');
      console.log(`- GET  http://localhost:${port}/api/port`);
      console.log(`- POST http://localhost:${port}/api/chat`);
      console.log('Use Ctrl+C to stop the server');
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
};

startServer();