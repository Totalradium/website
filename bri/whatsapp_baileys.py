import requests
import json
from django.conf import settings

class BaileysWhatsApp:
    def __init__(self):
        import os
        # Use environment variable for production, localhost for development
        self.base_url = os.getenv('WHATSAPP_SERVICE_URL', 'http://localhost:3001')
    
    def get_qr_code(self):
        """Get QR code for WhatsApp authentication"""
        try:
            response = requests.get(f"{self.base_url}/qr")
            return response.json()
        except requests.exceptions.RequestException:
            return {"error": "WhatsApp service not running"}
    
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