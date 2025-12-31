# Git push script
git config user.name "SUPFLOT Bot"
git config user.email "bot@supflot.local"

# Add all files
git add .

# Commit
git commit -m "feat: реализованы все недостающие функции - каталог, профиль, суточная аренда, модерация отзывов, управление сотрудниками, мультибронь"

# Check if remote exists
$remote = git remote -v
if ($remote) {
    git push
} else {
    Write-Host "Remote repository not configured. Please add remote first:"
    Write-Host "git remote add origin <your-repo-url>"
    Write-Host "git push -u origin main"
}

