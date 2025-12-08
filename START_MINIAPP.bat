@echo off
echo ====================================
echo   Запуск SUPFLOT Website + ngrok
echo ====================================
echo.

echo Запуск сайта...
start "SUPFLOT Website" cmd /k "cd orders_site && python app.py"

timeout /t 3 /nobreak >nul

echo Запуск ngrok...
start "ngrok" cmd /k "ngrok http 5000"

echo.
echo ====================================
echo   Сайт запущен на http://localhost:5000
echo   ngrok запущен - проверьте URL в консоли ngrok
echo ====================================
echo.
echo Скопируйте URL из ngrok (например: https://xxxx.ngrok.io)
echo и обновите MINIAPP_URL в .env файле
echo.
pause

