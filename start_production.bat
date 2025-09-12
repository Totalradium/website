@echo off
cd /d "C:\Users\A_R\Desktop\Brighway Site\website"
start /b node whatsapp_service/server.js
timeout /t 3 /nobreak >nul
gunicorn website.wsgi:application --bind 0.0.0.0:8000