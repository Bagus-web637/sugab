@echo off
title NEXUS IoT - Pos Pantau KP Server
cd /d "%~dp0"
echo ======================================================
echo    MENJALANKAN SERVER MONITORING POS PANTAU KP
echo ======================================================
echo.
echo Membuka browser ke http://localhost:8080 ...
start http://localhost:8080
echo.
echo Server sedang berjalan di background.
echo JANGAN TUTUP jendela ini selama ingin memantau dashboard.
echo (Tutup jendela ini jika ingin mematikan server)
echo.
python server.py
pause
