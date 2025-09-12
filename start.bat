@echo off
cd /d "C:\Users\A_R\Desktop\Brighway Site\website"
start /b npm start
timeout /t 3 /nobreak >nul
python manage.py runserver 0.0.0.0:8000