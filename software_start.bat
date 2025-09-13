@echo off
echo Starting WhatsApp Service and Django Server...

start "WhatsApp Service" cmd /k "cd whatsapp_service && node server.js"
timeout /t 3 /nobreak >nul
python manage.py runserver

pause