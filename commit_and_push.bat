@echo off
chcp 65001 >nul
cd /d "%~dp0"
git config user.name "SUPFLOT Bot"
git config user.email "bot@supflot.local"
git commit -m "feat: реализованы все недостающие функции - каталог, профиль, суточная аренда, модерация отзывов, управление сотрудниками, мультибронь"
git push -u origin main
pause

