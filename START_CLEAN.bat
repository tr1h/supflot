@echo off
title SUPFLOT - Чистый запуск
color 0A

echo ========================================
echo   SUPFLOT - Чистый запуск
echo ========================================
echo.

echo [1/4] Остановка старых процессов...
taskkill /F /IM ngrok.exe 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq SUPFLOT*" 2>nul
timeout /t 1 /nobreak >nul

echo [2/4] Запуск веб-сайта...
start "SUPFLOT Website" cmd /k "cd /d %~dp0orders_site && python app.py"
timeout /t 4 /nobreak >nul

echo [3/4] Запуск ngrok...
start "ngrok" cmd /k "cd /d %~dp0 && ngrok http 5000"
timeout /t 3 /nobreak >nul

echo [4/4] Готово!
echo.
echo ✅ Сайт: http://localhost:5000
echo ✅ Mini App: http://localhost:5000/miniapp/
echo ✅ ngrok: проверьте URL в окне ngrok
echo.
echo 📋 Следующие шаги:
echo    1. Скопируйте URL из окна ngrok
echo    2. Запустите UPDATE_MINIAPP_URL.bat
echo    3. Введите URL
echo    4. Запустите бота: python run_bot.py
echo.
echo ========================================
pause

