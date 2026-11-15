const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(express.json());

// Simple health check
app.get('/health', (req, res) => res.json({status: 'ok'}));

// Placeholder routes – actual modules will be added later
const camerasRouter = require('./routes/cameras');
const detectionsRouter = require('./routes/detections');

app.use('/api/v1/cameras', camerasRouter);
app.use('/api/v1/detections', detectionsRouter);

app.get('/', (req, res) => res.send('ROADGUARD Backend API'));

const server = http.createServer(app);
const io = new Server(server, { cors: { origin: '*'} });

io.on('connection', (socket) => {
  console.log('client connected', socket.id);
  // future: forward detection, risk, alerts streams
});

const PORT = process.env.PORT || 4000;
server.listen(PORT, () => console.log(`Backend listening on ${PORT}`));

