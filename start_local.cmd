@echo off
chcp 65001 >nul
title Omnom — LOCAL START

cd /d "%~dp0"

echo ====================================
echo   Omnom ^& SweetMe — локальный запуск
echo ====================================
echo.

:: 1. Авторизация ngrok
echo [1/4] Авторизация ngrok...
ngrok authtoken 3FIgDteWuRUj0QV8WQ99mw4w7VC_2VmE1p1fFm9wKB5VaHwto 2>nul

:: 2. Установка зависимостей (если нужно)
echo [2/4] Проверка npm...
if not exist "node_modules" (
    call npm install
)

:: 3. Запуск Python Telegram handler
echo [3/4] Запуск Telegram handler...
start "Omnom Handler" cmd /c "chcp 65001 >nul && cd /d "%~dp0worker" && set BOT_TOKEN=8518399300:AAEX-pbC-s2x7iId8x4-6jKqdBjdBKD9aTs && set ADMIN_CHAT_ID=330619718 && python telegram_handler.py"

:: 4. Запуск ngrok
echo [4/4] Запуск ngrok...
echo.
echo ====================================
echo   ГОТОВО! Открой на телефоне:
echo.
echo   https://newacctv13-blip.github.io/webapp/?worker=https://XXXX.ngrok-free.app
echo.
echo   ^(замени XXXX на адрес из окна ngrok^)
echo.
echo   Или используй Python-скрипт ^(сам обновит GitHub^):
echo   python worker\start_online.py
echo ====================================
echo.

ngrok http 8765

echo.
pause
