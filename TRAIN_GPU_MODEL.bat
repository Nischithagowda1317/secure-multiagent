@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0train_gpu_model.ps1" %*
if errorlevel 1 pause
