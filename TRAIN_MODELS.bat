@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0train_models.ps1" %*
if errorlevel 1 pause
