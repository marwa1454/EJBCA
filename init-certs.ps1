#!/usr/bin/env pwsh
# Script d'initialisation - Génère les certificats automatiquement

Write-Host "🔧 Initialisation de l'environnement EJBCA-FastAPI" -ForegroundColor Cyan
Write-Host ""

# Configuration
$USERNAME = "apiuser"
$PASSWORD = "Marwa77233473"
$CN = "API User"
$ORGANIZATION = "EJBCA API"
$EMAIL = "api@ejbca.local"
$CA_NAME = "ManagementCA"

# Vérifier si les certificats existent
if ((Test-Path "./certs/apiuser.p12") -and (Test-Path "./certs/ca_cert.pem")) {
    Write-Host "✅ Certificats déjà présents" -ForegroundColor Green
    Write-Host "   - ./certs/apiuser.p12"
    Write-Host "   - ./certs/ca_cert.pem"
    exit 0
}

Write-Host "⚙️  Génération des certificats API..." -ForegroundColor Yellow

# Créer le dossier certs
if (-not (Test-Path "./certs")) {
    New-Item -ItemType Directory -Path "./certs" | Out-Null
}

# Supprimer l'utilisateur s'il existe
Write-Host "1️⃣ Nettoyage de l'utilisateur existant..."
docker exec ejbca-ca bash -c "echo 'y' | /opt/keyfactor/bin/ejbca.sh ra delendentity --username $USERNAME" 2>$null | Out-Null

# Créer l'utilisateur
Write-Host "2️⃣ Création de l'utilisateur API..."
docker exec ejbca-ca /opt/keyfactor/bin/ejbca.sh ra addendentity `
    --username "$USERNAME" `
    --dn "CN=$CN,O=$ORGANIZATION" `
    --caname "$CA_NAME" `
    --type 1 `
    --token P12 `
    --password "$PASSWORD" `
    --email "$EMAIL" `
    --certprofile ENDUSER `
    --eeprofile EMPTY | Out-Null

# Définir le mot de passe
Write-Host "3️⃣ Configuration du mot de passe..."
docker exec ejbca-ca /opt/keyfactor/bin/ejbca.sh ra setclearpwd `
    --username "$USERNAME" `
    --password "$PASSWORD" | Out-Null

# Créer répertoire temporaire
docker exec ejbca-ca mkdir -p /tmp/api-certs | Out-Null

# Générer le certificat
Write-Host "4️⃣ Génération du certificat P12..."
$batchResult = docker exec ejbca-ca /opt/keyfactor/bin/ejbca.sh batch --username "$USERNAME" -dir /tmp/api-certs 2>&1

# Vérifier où le fichier a été généré
$p12Path = docker exec ejbca-ca bash -c "find /tmp/api-certs -name '*.pem' -o -name '*.p12' | head -1" 2>$null

if ($p12Path) {
    Write-Host "5️⃣ Copie du certificat P12..."
    Write-Host "   Trouvé: $p12Path"
    docker cp "ejbca-ca:$p12Path" ./certs/apiuser.p12
} else {
    Write-Host "❌ Certificat P12 non trouvé" -ForegroundColor Red
    Write-Host "Résultat batch:"
    Write-Host $batchResult
    exit 1
}

# Obtenir le certificat CA
Write-Host "6️⃣ Récupération du certificat CA..."
docker exec ejbca-ca /opt/keyfactor/bin/ejbca.sh ca getcacert `
    --caname "$CA_NAME" `
    -f /tmp/ca-cert.pem | Out-Null

docker cp ejbca-ca:/tmp/ca-cert.pem ./certs/ca_cert.pem

# Attribuer le rôle Super Administrator
Write-Host "7️⃣ Attribution du rôle Super Administrator..."
docker exec ejbca-ca /opt/keyfactor/bin/ejbca.sh roles addrolemember `
    --role "Super Administrator Role" `
    --caname "$CA_NAME" `
    --with "CertificateAuthenticationToken:WITH_COMMONNAME" `
    --value "$CN" 2>$null | Out-Null

# Nettoyer
docker exec ejbca-ca rm -rf /tmp/api-certs /tmp/ca-cert.pem | Out-Null

Write-Host ""
Write-Host "✅ CERTIFICATS GÉNÉRÉS AVEC SUCCÈS!" -ForegroundColor Green
Write-Host "   - apiuser.p12 (certificat + clé)" -ForegroundColor White
Write-Host "   - ca_cert.pem (certificat CA)" -ForegroundColor White
Write-Host ""
Write-Host "📦 Mot de passe: $PASSWORD" -ForegroundColor Yellow
