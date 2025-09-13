const { default: makeWASocket, DisconnectReason, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const express = require('express');
const QRCode = require('qrcode');

const app = express();
app.use(express.json());

let sock;
let qrCodeData = null;
let isConnected = false;

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');
    
    sock = makeWASocket({
        auth: state,
        printQRInTerminal: false,
        browser: ['Chrome (Linux)', '', ''],
        syncFullHistory: false,
        markOnlineOnConnect: false,
        generateHighQualityLinkPreview: false,
        defaultQueryTimeoutMs: 60000,
        connectTimeoutMs: 60000,
        keepAliveIntervalMs: 30000,
        emitOwnEvents: false
    });

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        
        if (qr) {
            console.log('New QR code generated');
            QRCode.toDataURL(qr, (err, url) => {
                if (!err) {
                    qrCodeData = url;
                }
            });
        }
        
        if (connection === 'close') {
            const statusCode = (lastDisconnect?.error)?.output?.statusCode;
            console.log('Connection closed due to ', lastDisconnect?.error);
            
            isConnected = false;
            qrCodeData = null;
            
            if (statusCode === 401) {
                console.log('❌ WhatsApp blocked this connection (401). Auto-deleting auth folder and restarting...');
                const fs = require('fs');
                const path = require('path');
                
                // Delete auth folder
                try {
                    fs.rmSync('../auth_info_baileys', { recursive: true, force: true });
                    console.log('🗑️ Auth folder deleted');
                } catch (err) {
                    console.log('⚠️ Could not delete auth folder:', err.message);
                }
                
                // Restart after 5 seconds
                setTimeout(() => {
                    console.log('🔄 Restarting WhatsApp connection...');
                    connectToWhatsApp();
                }, 5000);
            } else if (statusCode === DisconnectReason.loggedOut) {
                console.log('📱 Logged out. Need to scan QR again.');
            } else {
                console.log('🔄 Connection lost. Will auto-reconnect in 10 seconds...');
                setTimeout(() => {
                    connectToWhatsApp();
                }, 10000);
            }
        } else if (connection === 'open') {
            console.log('WhatsApp connected successfully!');
            isConnected = true;
            qrCodeData = null;
        } else if (connection === 'connecting') {
            console.log('Connecting to WhatsApp...');
            isConnected = false;
        }
    });

    sock.ev.on('creds.update', saveCreds);
}

// API Routes
app.get('/qr', (req, res) => {
    if (qrCodeData) {
        res.json({ qr: qrCodeData, status: 'qr_ready' });
    } else if (isConnected) {
        res.json({ status: 'connected' });
    } else {
        // Force reconnection to generate new QR
        if (!sock || sock.ws.readyState !== 1) {
            connectToWhatsApp();
        }
        res.json({ status: 'connecting', message: 'Generating new QR code...' });
    }
});

app.post('/send', async (req, res) => {
    const { phone, message } = req.body;
    
    if (!isConnected) {
        return res.status(400).json({ error: 'WhatsApp not connected' });
    }
    
    try {
        const jid = phone.includes('@') ? phone : `${phone}@s.whatsapp.net`;
        
        // Add random delay to mimic human behavior
        await new Promise(resolve => setTimeout(resolve, Math.random() * 2000 + 1000));
        
        await sock.sendMessage(jid, { text: message });
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/status', (req, res) => {
    res.json({ connected: isConnected });
});

const PORT = process.env.WHATSAPP_PORT || 3001;
app.listen(PORT, 'localhost', () => {
    console.log(`WhatsApp service running on port ${PORT}`);
    connectToWhatsApp();
});