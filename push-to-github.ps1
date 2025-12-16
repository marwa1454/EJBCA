# Script pour pousser le code vers GitHub
Write-Host "=== Nettoyage des anciens .git ===" -ForegroundColor Yellow
Remove-Item -Path ".git" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "../.git" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "../../.git" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "✅ Nettoyage terminé`n" -ForegroundColor Green

Write-Host "=== Initialisation de Git ===" -ForegroundColor Yellow
git init
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Git initialisé`n" -ForegroundColor Green
} else {
    Write-Host "❌ Erreur lors de l'initialisation de Git" -ForegroundColor Red
    exit 1
}

Write-Host "=== Configuration de Git ===" -ForegroundColor Yellow
git config user.name "marwa1454"
git config user.email "marwa@example.com"
Write-Host "✅ Configuration terminée`n" -ForegroundColor Green

Write-Host "=== Ajout du remote GitHub ===" -ForegroundColor Yellow
git remote add origin https://github.com/marwa1454/EJBCA.git
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Remote ajouté`n" -ForegroundColor Green
} else {
    Write-Host "❌ Erreur lors de l'ajout du remote" -ForegroundColor Red
    exit 1
}

Write-Host "=== Ajout des fichiers ===" -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Fichiers ajoutés`n" -ForegroundColor Green
} else {
    Write-Host "❌ Erreur lors de l'ajout des fichiers" -ForegroundColor Red
    exit 1
}

Write-Host "=== Vérification des fichiers à commiter ===" -ForegroundColor Yellow
git status --short
Write-Host ""

Write-Host "=== Commit des fichiers ===" -ForegroundColor Yellow
git commit -m "Initial commit: EJBCA FastAPI Gateway with certificate authentication"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Commit réussi`n" -ForegroundColor Green
} else {
    Write-Host "❌ Erreur lors du commit" -ForegroundColor Red
    exit 1
}

Write-Host "=== Renommage de la branche en main ===" -ForegroundColor Yellow
git branch -M main
Write-Host "✅ Branche renommée en main`n" -ForegroundColor Green

Write-Host "=== Push vers GitHub (FORCE) ===" -ForegroundColor Yellow
git push -u origin main --force
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ ✅ ✅ CODE POUSSÉ AVEC SUCCÈS VERS GITHUB! ✅ ✅ ✅" -ForegroundColor Green
    Write-Host "Repository: https://github.com/marwa1454/EJBCA" -ForegroundColor Cyan
} else {
    Write-Host "`n❌ Erreur lors du push vers GitHub" -ForegroundColor Red
    Write-Host "Vérifiez vos permissions GitHub et votre connexion" -ForegroundColor Yellow
    exit 1
}
