@echo off
title SUPFLOT - Запуск всего
color 0A

echo ========================================
echo   SUPFLOT - Запуск всех сервисов
echo ========================================
echo.

echo [1/3] Запуск веб-сайта...
start "SUPFLOT Website" cmd /k "cd /d %~dp0orders_site && python app.py"
timeout /t 3 /nobreak >nul

echo [2/3] Запуск ngrok...
start "ngrok" cmd /k "cd /d %~dp0 && ngrok http 5000"
timeout /t 2 /nobreak >nul

echo [3/3] Инструкция:
echo.
echo ✅ Сайт запущен на http://localhost:5000
echo ✅ ngrok запущен - проверьте URL в окне ngrok
echo.
echo 📋 Следующие шаги:
echo    1. Скопируйте URL из окна ngrok (например: https://xxxx.ngrok.io)
echo    2. Запустите UPDATE_MINIAPP_URL.bat
echo    3. Введите URL от ngrok
echo    4. Запустите бота: python run_bot.py
echo.
echo ========================================
pause

