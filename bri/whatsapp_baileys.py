import requests
import json
from django.conf import settings

class BaileysWhatsApp:
    def __init__(self):
        import os
        # Auto-detect WhatsApp service port
        self.base_url = os.environ.get('WHATSAPP_SERVICE_URL', self._detect_service_url())
    
    def _detect_service_url(self):
        """Auto-detect WhatsApp service port"""
        import socket
        ports = [3001, 3000, 8080, 5000]
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                if result == 0:
                    return f'http://localhost:{port}'
            except:
                continue
        return 'http://localhost:3001'  # fallback
    
    def get_qr_code(self):
        """Get QR code for WhatsApp authentication"""
        try:
            response = requests.get(f"{self.base_url}/qr", timeout=5)
            return response.json()
        except requests.exceptions.RequestException:
            # Try to re-detect service if connection fails
            self.base_url = self._detect_service_url()
            try:
                response = requests.get(f"{self.base_url}/qr", timeout=5)
                return response.json()
            except:
                return {"error": "WhatsApp service not available", "qr": None}
    
    def send_message(self, phone, message):
        """Send WhatsApp message"""
        try:
            # Format phone number
            if not phone.startswith('+'):
                phone = f"+{phone}"
            phone = phone.replace('+', '').replace('-', '').replace(' ', '')
            
            response = requests.post(f"{self.base_url}/send", json={
                "phone": phone,
                "message": message
            })
            return response.json()
        except requests.exceptions.RequestException:
            return {"error": "WhatsApp service not running"}
    
    def get_status(self):
        """Check WhatsApp connection status"""
        try:
            response = requests.get(f"{self.base_url}/status")
            return response.json()
        except requests.exceptions.RequestException:
            return {"connected": False, "error": "Service not running"}