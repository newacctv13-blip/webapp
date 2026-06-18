@echo off
cd /d "%~dp0"
chcp 65001 >nul
title Omnom Handler + ngrok

echo ====================================
echo  Omnom — запуск handler + ngrok
echo ====================================
echo.

:: Запускаем Python handler в новом окне
start "Omnom Handler" cmd /c "chcp 65001 >nul && set BOT_TOKEN=8518399300:AAEX-pbC-s2x7iId8x4-6jKqdBjdBKD9aTs && set ADMIN_CHAT_ID=330619718 && python telegram_handler.py"

:: Ждём старта handler
ping 127.0.0.1 -n 3 >nul

:: Запускаем ngrok
echo Запуск ngrok... Убедитесь, что ngrok.exe есть в PATH!
echo.
echo После запуска скопируйте https-ссылку (например https://xxxx.ngrok-free.app)
echo и откройте сайт с параметром:
echo.
echo   https://newacctv13-blip.github.io/webapp/?worker=https://xxxx.ngrok-free.app
echo.
echo На телефоне заказ пойдёт через ngrok на ваш компьютер -> Telegram
echo.
ngrok http 8765
pause
