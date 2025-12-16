#!/usr/bin/env pwsh
# Script pour créer un certificat administrateur pour l'interface web EJBCA

Write-Host "🔐 Création du certificat Super Admin pour navigateur" -ForegroundColor Cyan
Write-Host ""

# Configuration
$ADMIN_USERNAME = "webadmin"
$ADMIN_PASSWORD = "Marwa77233473"
$CN = "Web Administrator"
$ORGANIZATION = "EJBCA Administration"
$EMAIL = "admin@ejbca.local"
$CA_NAME = "ManagementCA"

Write-Host "⚙️  Configuration:" -ForegroundColor Yellow
Write-Host "   Username: $ADMIN_USERNAME"
Write-Host "   CN: $CN"
Write-Host "   CA: $CA_NAME"
Write-Host ""

# Supprimer l'utilisateur s'il existe
Write-Host "1️⃣  Suppression utilisateur existant..." -ForegroundColor Yellow
docker exec ejbca-ca /opt/keyfactor/bin/ejbca.sh ra setclearpwd --username $ADMIN_USERNAME --password dummy 2>&1 | Out-Null
docker exec ejbca-ca /opt/keyfactor/bin/ejbca.sh ra revokeuser --username $ADMIN_USERNAME -r 0 2>&1 | Out-Null
docker exec ejbca-ca /opt/keyfactor/bin/ejbca.sh ra deluser --username $ADMIN_USERNAME 2>&1 | Out-Null

# Créer l'utilisateur
Write-Host "2️⃣  Création utilisateur '$ADMIN_USERNAME'..." -ForegroundColor Yellow
$result = docker exec ejbca-ca /opt/keyfactor/bin/ejbca.sh ra addendentity `
    --username $ADMIN_USERNAME `
    --password $ADMIN_PASSWORD `
    --dn "CN=$CN,O=$ORGANIZATION" `
    --caname $CA_NAME `
    --email $EMAIL `
    --type 1 `
    --token P12 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors de la création de l'utilisateur" -ForegroundColor Red
    Write-Host $result
    exit 1
}

Write-Host "   ✅ Utilisateur créé" -ForegroundColor Green

# Générer le certificat P12
Write-Host "3️⃣  Génération du certificat P12..." -ForegroundColor Yellow
$batchResult = docker exec ejbca-ca /opt/keyfactor/bin/ejbca.sh batch $ADMIN_USERNAME 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors de la génération du certificat" -ForegroundColor Red
    Write-Host $batchResult
    exit 1
}

Write-Host "   ✅ Certificat généré dans le container" -ForegroundColor Green

# Trouver le fichier P12 généré
Write-Host "4️⃣  Recherche du fichier P12..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

$p12File = docker exec ejbca-ca bash -c "find /tmp -name '$ADMIN_USERNAME.p12' 2>/dev/null | head -1" 2>&1

if ([string]::IsNullOrWhiteSpace($p12File)) {
    Write-Host "❌ Fichier P12 non trouvé" -ForegroundColor Red
    exit 1
}

Write-Host "   ✅ Trouvé: $p12File" -ForegroundColor Green

# Copier le certificat
Write-Host "5️⃣  Copie du certificat..." -ForegroundColor Yellow
if (-not (Test-Path "./certs")) {
    New-Item -ItemType Directory -Path "./certs" | Out-Null
}

docker cp "ejbca-ca:$p12File" "./certs/webadmin.p12" 2>&1 | Out-Null

if (-not (Test-Path "./certs/webadmin.p12")) {
    Write-Host "❌ Échec de la copie" -ForegroundColor Red
    exit 1
}

Write-Host "   ✅ Certificat copié vers: ./certs/webadmin.p12" -ForegroundColor Green

# Ajouter au rôle Super Administrator
Write-Host "6️⃣  Ajout au rôle Super Administrator..." -ForegroundColor Yellow
$roleResult = docker exec ejbca-ca /opt/keyfactor/bin/ejbca.sh roles addrolemember `
    --role "Super Administrator Role" `
    --caname $CA_NAME `
    --with CertificateAuthenticationToken:WITH_COMMONNAME `
    --value "$CN" `
    --description "Web Administrator" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Le membre existe peut-être déjà" -ForegroundColor Yellow
} else {
    Write-Host "   ✅ Rôle assigné" -ForegroundColor Green
}

# Vérification
Write-Host ""
Write-Host "7️⃣  Vérification..." -ForegroundColor Yellow
$fileSize = (Get-Item "./certs/webadmin.p12").Length
Write-Host "   Taille du fichier: $fileSize bytes" -ForegroundColor Cyan

Write-Host ""
Write-Host "✅ CERTIFICAT CRÉÉ AVEC SUCCÈS!" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Emplacement: ./certs/webadmin.p12" -ForegroundColor Cyan
Write-Host "🔑 Mot de passe: $ADMIN_PASSWORD" -ForegroundColor Cyan
Write-Host ""
Write-Host "📌 PROCHAINES ÉTAPES:" -ForegroundColor Yellow
Write-Host "   1. Double-cliquez sur 'certs\webadmin.p12'" -ForegroundColor White
Write-Host "   2. Saisissez le mot de passe: $ADMIN_PASSWORD" -ForegroundColor White
Write-Host "   3. Importez dans: 'Utilisateur actuel' > 'Personnel'" -ForegroundColor White
Write-Host "   4. Ouvrez: https://localhost:8443/ejbca/adminweb/" -ForegroundColor White
Write-Host "   5. Sélectionnez le certificat 'Web Administrator' quand demandé" -ForegroundColor White
Write-Host ""
