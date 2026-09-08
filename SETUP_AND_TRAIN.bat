@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_and_train.ps1" %*
if errorlevel 1 pause
