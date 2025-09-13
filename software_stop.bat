@echo off
echo Stopping services...
taskkill /f /im node.exe 2>nul
taskkill /f /im python.exe 2>nul
echo Services stopped.
pause