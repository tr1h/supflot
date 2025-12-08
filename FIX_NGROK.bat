@echo off
echo ========================================
echo   Остановка старых процессов ngrok
echo ========================================
echo.

taskkill /F /IM ngrok.exe 2>nul
if %errorlevel%==0 (
    echo ✅ Старые процессы ngrok остановлены
) else (
    echo ℹ️  Активных процессов ngrok не найдено
)

echo.
echo Теперь можно запустить ngrok заново:
echo   ngrok http 5000
echo.
pause

