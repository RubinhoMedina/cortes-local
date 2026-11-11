@echo off
cd /d "%~dp0"
"%USERPROFILE%\edicao-ia\.venv\Scripts\python.exe" -X utf8 fluxo.py --auto-select --auto-frame %*
exit /b %errorlevel%
