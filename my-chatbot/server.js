import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import net from 'net';
import chatHandler from './api/chat.js';

dotenv.config();

const app = express();

// Utility function to check if a port is available
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

// Find an available port
const findAvailablePort = async (startPort) => {
  let port = startPort;
  while (!(await isPortAvailable(port))) {
    console.log(`Port ${port} is in use, trying next port...`);
    port++;
  }
  return port;
};

// Dynamic CORS configuration
const corsOptions = {
  origin: function (origin, callback) {
    // Allow requests with no origin (like mobile apps or curl requests)
    if (!origin) return callback(null, true);
    
    // Check if the origin matches our pattern
    const allowedOrigins = Array.from({ length: 20 }, (_, i) => i + 5173)
      .flatMap(port => [`http://localhost:${port}`, `http://127.0.0.1:${port}`]);
    
    if (allowedOrigins.indexOf(origin) !== -1) {
      callback(null, true);
    } else {
      console.log(`Origin ${origin} not allowed by CORS`);
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
};

app.use(cors(corsOptions));
app.options('*', cors(corsOptions));

app.use(express.json());

// Enhanced logging middleware with timing
app.use((req, res, next) => {
  const start = Date.now();
  const timestamp = new Date().toISOString();
  const requestId = Math.random().toString(36).substring(7);

  console.log(`\n=== Request ${requestId} Started ===`);
  console.log(`Time: ${timestamp}`);
  console.log(`${req.method} ${req.path}`);
  console.log('Headers:', JSON.stringify(req.headers, null, 2));
  
  if (req.body && Object.keys(req.body).length > 0) {
    console.log('Body:', JSON.stringify(req.body, null, 2));
  }

  // Capture response
  const oldSend = res.send;
  res.send = function(data) {
    const duration = Date.now() - start;
    console.log(`\n=== Request ${requestId} Completed ===`);
    console.log(`Duration: ${duration}ms`);
    console.log('Response:', typeof data === 'string' ? data : JSON.stringify(data, null, 2));
    console.log('===============================\n');
    oldSend.apply(res, arguments);
  };

  next();
});

// Enhanced port discovery endpoint
app.get('/api/port', (req, res) => {
  const port = app.get('port');
  console.log('Port discovery request received:');
  console.log('- Port:', port);
  console.log('- Origin:', req.headers.origin);
  res.json({ 
    port: port, 
    status: 'active',
    serverTime: new Date().toISOString()
  });
});

// Enhanced chat endpoint with timeout
app.post('/api/chat', async (req, res) => {
  const requestId = Math.random().toString(36).substring(7);
  console.log(`\n=== Chat Request ${requestId} ===`);
  console.log('Time:', new Date().toISOString());
  console.log('Body:', req.body);

  const TIMEOUT = 30000; // 30 second timeout

  try {
    if (!req.body.message) {
      throw new Error('Message is required');
    }

    // Create a timeout promise
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Request timeout after 30 seconds')), TIMEOUT);
    });

    // Race between the chat handler and the timeout
    const result = await Promise.race([
      chatHandler(req.body),
      timeoutPromise
    ]);

    console.log(`Chat Request ${requestId} completed successfully`);
    console.log('Response:', result);
    res.json(result);

  } catch (error) {
    console.error(`Error in chat request ${requestId}:`, error);
    const errorResponse = {
      error: error.message,
      type: error.name,
      requestId: requestId
    };

    // Add stack trace in development
    if (process.env.NODE_ENV === 'development') {
      errorResponse.stack = error.stack;
    }

    res.status(500).json(errorResponse);
  }
});

// Add a health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    time: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: err.message,
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
});

// Server startup with enhanced error handling
const startServer = async () => {
  const preferredPort = 3003;
  try {
    const port = await findAvailablePort(preferredPort);
    app.set('port', port);

    console.log('\n=== Starting Bot Initialization ===');
    chatHandler({ message: "init" })  // Non-blocking initialization
      .then(() => console.log('Bot initialization complete!'))
      .catch(err => console.error('Bot initialization error:', err));
    
    const server = app.listen(port, () => {
      console.log('\n=== Server Started ===');
      console.log(`Time: ${new Date().toISOString()}`);
      console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
      console.log(`Port: ${port}`);
      console.log('\nAvailable endpoints:');
      console.log(`- GET  http://localhost:${port}/api/port    (Port discovery)`);
      console.log(`- POST http://localhost:${port}/api/chat    (Chat endpoint)`);
      console.log(`- GET  http://localhost:${port}/api/health  (Health check)`);
      console.log('\nPress Ctrl+C to stop the server');
      console.log('=====================\n');
    });

    // Graceful shutdown handling
    process.on('SIGTERM', () => {
      console.log('SIGTERM received. Shutting down gracefully...');
      server.close(() => {
        console.log('Server closed');
        process.exit(0);
      });
    });

  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
};

// Global error handlers
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

startServer();