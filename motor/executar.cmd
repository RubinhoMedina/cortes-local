@echo off
cd /d "%~dp0"
"%USERPROFILE%\edicao-ia\.venv\Scripts\python.exe" -X utf8 executor.py %*
exit /b %errorlevel%
