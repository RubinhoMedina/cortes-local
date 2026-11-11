#!/usr/bin/env node

import 'dotenv/config';
import { startMcpServer } from './server.js';
import { hasConfiguredYouTubeApiKey } from './services/youtube-client.js';

// Check for required environment variables
if (!hasConfiguredYouTubeApiKey()) {
    console.error('YouTube API key pending. Transcript tools are available.');
    console.error('Configure a YouTube Data API key to enable search and statistics.');

}

// Start the MCP server
startMcpServer()
    .then(() => {
        console.error('YouTube MCP Server started successfully');
    })
    .catch(error => {
        console.error('Failed to start YouTube MCP Server:', error);
        process.exit(1);
    });
