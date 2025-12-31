@echo off
echo ====================================
echo   Обновление MINIAPP_URL в .env
echo ====================================
echo.
set /p NGROK_URL="Введите URL от ngrok (например: https://xxxx.ngrok.io): "

if "%NGROK_URL%"=="" (
    echo Ошибка: URL не введен
    pause
    exit /b 1
)

echo.
echo Обновление .env файла...

REM Проверяем, есть ли уже MINIAPP_URL
findstr /C:"MINIAPP_URL" .env >nul 2>&1
if %errorlevel%==0 (
    REM Заменяем существующую строку
    powershell -Command "(Get-Content .env) -replace 'MINIAPP_URL=.*', 'MINIAPP_URL=%NGROK_URL%/miniapp/' | Set-Content .env"
    echo ✅ MINIAPP_URL обновлен
) else (
    REM Добавляем новую строку
    echo MINIAPP_URL=%NGROK_URL%/miniapp/ >> .env
    echo ✅ MINIAPP_URL добавлен
)

echo.
echo Готово! Теперь перезапустите бота.
echo.
pause

