const express = require('express');
const { exec } = require('child_process');
const cors = require('cors');
const app = express();
const port = 3001;

// Enable CORS for all origins
app.use(cors({
    origin: '*',
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use(express.json());

// Handle preflight requests
app.options('*', cors());

// Endpoint to start docker-compose and get container sizes
app.post('/start-comparison', (req, res) => {
    console.log('🚀 Starting Docker Compose...');
    
    // Start docker-compose in detached mode
    exec('docker-compose up --build -d', (error, stdout, stderr) => {
        if (error) {
            console.error(`❌ Error starting Docker Compose: ${error}`);
            console.error(`STDERR: ${stderr}`);
            return res.status(500).json({ error: 'Failed to start Docker Compose', details: error.message });
        }
        
        console.log('✅ Docker Compose started successfully');
        console.log('📦 Docker output:', stdout);
        
        // Wait a bit for containers to start, then get container sizes
        setTimeout(() => {
            console.log('⏳ Waiting for containers to initialize...');
            exec('docker ps --format "{{.Names}}\\t{{.Size}}"', (error, stdout, stderr) => {
                if (error) {
                    console.error(`❌ Error getting container sizes: ${error}`);
                    console.error(`STDERR: ${stderr}`);
                    return res.status(500).json({ error: 'Failed to get container sizes', details: error.message });
                }
                
                console.log('📊 Raw container data:', stdout);
                
                // Parse docker output - handle both single line and multi-line output
                console.log('📊 Raw stdout:', JSON.stringify(stdout));
                const lines = stdout.trim().split('\\n').filter(line => line.trim());
                console.log('📊 Split lines:', lines);
                const containers = [];
                
                lines.forEach((line, index) => {
                    console.log(`📊 Processing line ${index}:`, JSON.stringify(line));
                    // Split by tab character and clean up
                    const parts = line.split('\\t').map(part => part.trim());
                    console.log(`📊 Split parts:`, parts);
                    const name = parts[0] || '';
                    const size = parts[1] || '';
                    // Only include main application containers, exclude database containers
                    if (name && name.includes('postgres')) {
                        console.log(`📦 Skipping database container: ${name}`);
                        return;
                    }
                    console.log(`📦 Container: ${name} - Size: ${size}`);
                    containers.push({ name, size });
                });
                
                console.log(`✅ Found ${containers.length} containers`);
                res.json({ containers });
            });
        }, 5000); // Wait 5 seconds for containers to start
    });
});

// Endpoint to stop docker-compose
app.post('/stop-comparison', (req, res) => {
    console.log('🛑 Stopping Docker Compose...');
    exec('docker-compose down', (error, stdout, stderr) => {
        if (error) {
            console.error(`❌ Error stopping Docker Compose: ${error}`);
            console.error(`STDERR: ${stderr}`);
            return res.status(500).json({ error: 'Failed to stop Docker Compose', details: error.message });
        }
        
        console.log('✅ Docker Compose stopped successfully');
        console.log('📦 Docker output:', stdout);
        res.json({ message: 'Docker Compose stopped successfully' });
    });
});

app.listen(port, () => {
    console.log(`🌐 Docker server listening at http://localhost:${port}`);
    console.log('📡 Ready to handle Docker diagnostic requests');
    console.log('🔒 CORS enabled for all origins');
});
