# VISION-GUARD
VisionGuard is a full-stack AI system featuring a modular architecture with a core AI engine, backend API, and interactive frontend UI. Built for real-time intelligent processing and seamless user control, it includes a one-click Windows launcher for quick deployment across all integrated services.
@echo off
title VisionGuard Enterprise Launcher
color 0A

echo ===================================================
echo  🚀 STARTING VISION GUARD PRO - MICROSERVICES...
echo ===================================================

echo [1] Starting Backend Server (FastAPI + SQLite)...
start "VisionGuard - Backend Server" cmd /k "cd backend_api && python main_server.py"
timeout /t 3 /nobreak > NUL

echo [2] Starting AI Engine (YOLO + Face Recognition)...
start "VisionGuard - AI Engine" cmd /k "cd ai_engine && python main.py"
timeout /t 5 /nobreak > NUL

echo [3] Starting Frontend Dashboard (PyQt6 UI)...
start "VisionGuard - Dashboard" cmd /k "cd frontend_ui && python main_dashboard.py"

echo ===================================================
echo  ✅ ALL SYSTEMS ONLINE! 
echo  You can monitor the active terminals.
echo ===================================================
pause
