# EJBCA FastAPI Gateway

API REST Gateway pour EJBCA PKI (Public Key Infrastructure) avec authentification SOAP via certificat client.

## 🚀 Démarrage Rapide

```powershell
# 1. Démarrer les conteneurs
docker-compose up -d

# 2. Générer les certificats API (mot de passe: Marwa77233473)
.\init-certs.ps1

# 3. Accéder à l'API
# - API REST: http://localhost:8000
# - Documentation: http://localhost:8000/docs
```

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Client REST   │────▶│  FastAPI App    │────▶│   EJBCA CA      │
│   (Port 8000)   │     │  (Gateway)      │     │   (Port 8443)   │
│                 │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                        ┌────────▼────────┐
                        │                 │
                        │    MariaDB      │
                        │   (Port 3306)   │
                        │                 │
                        └─────────────────┘
```

## 📋 Prérequis

- Docker & Docker Compose
- OpenSSL (pour extraction des certificats)
- 4 Go RAM minimum
- 20 Go espace disque

## 🚀 Déploiement

### 1. Cloner et démarrer les services

```bash
git clone <repo>
cd ejbca-fastapi
docker compose up -d
```

### 2. Attendre qu'EJBCA soit prêt (~2-3 minutes)

```bash
# Vérifier le health
docker exec ejbca-ca curl -sf http://localhost:8080/ejbca/publicweb/healthcheck/ejbcahealth
```

### 3. Configurer SSL (script automatique)

```bash
chmod +x deployment/setup-ssl.sh
./deployment/setup-ssl.sh
```

Ce script :
- Crée un utilisateur admin `soapadmin` dans EJBCA
- Génère un certificat P12 pour l'authentification
- Extrait les fichiers PEM (cert + key)
- Configure le truststore EJBCA
- Ajoute les droits Super Administrator

### 4. Redémarrer FastAPI

```bash
docker compose restart fastapi-app
```

## 🔐 Certificats

Après le setup, les certificats sont dans `./certs/` :

| Fichier | Description |
|---------|-------------|
| `soapadmin.p12` | Certificat PKCS#12 (mot de passe: `soapadmin123`) |
| `soapadmin_cert.pem` | Certificat client PEM |
| `soapadmin_key.pem` | Clé privée PEM |
| `ManagementCA.pem` | Certificat de la CA |

## 📡 Endpoints API

### Base URL
```
http://<server>:8000
```

### Health Check
```bash
GET /health
```
Réponse :
```json
{
  "status": "healthy",
  "version": "5.0.0",
  "service": "EJBCA SOAP Gateway",
  "soap_connected": true,
  "timestamp": "2025-12-02T15:17:36.170828"
}
```

### Documentation Interactive
```
GET /docs      # Swagger UI
GET /redoc     # ReDoc
```

---

## 🔧 Endpoints SOAP

### Informations CA

#### Version EJBCA
```bash
GET /soap/getEjbcaVersion
```
Réponse :
```json
{
  "method": "getEjbcaVersion",
  "version": "EJBCA 8.2.0.1 Community"
}
```

#### Liste des CAs
```bash
GET /soap/getAvailableCAs
```
Réponse :
```json
{
  "method": "getAvailableCAs",
  "total": 1,
  "cas": [
    {
      "name": "ManagementCA",
      "ca_id": 242899634,
      "subject_dn": "UID=...,CN=ManagementCA,O=EJBCA Container Quickstart"
    }
  ]
}
```

#### Test Connexion SOAP
```bash
GET /soap/test
```
Réponse :
```json
{
  "connected": true,
  "wsdl_url": "https://ejbca-ca:8443/ejbca/ejbcaws/ejbcaws?wsdl",
  "total_operations": 60,
  "sample_operations": ["addSubjectToRole", "certificateRequest", "editUser", "..."]
}
```

---

### Gestion Utilisateurs

#### Créer/Modifier Utilisateur
```bash
POST /soap/editUser
Content-Type: application/json

{
  "username": "testuser",
  "password": "secret123",
  "clear_pwd": true,
  "subject_dn": "CN=Test User,O=MyOrg,C=FR",
  "ca_name": "ManagementCA",
  "end_entity_profile": "EMPTY",
  "certificate_profile": "ENDUSER",
  "token_type": "USERGENERATED",
  "status": 10
}
```

#### Supprimer Utilisateur
```bash
POST /soap/deleteUser?username=testuser
```

#### Révoquer Utilisateur
```bash
POST /soap/revokeUser
Content-Type: application/json

{
  "username": "testuser",
  "reason": 0,
  "delete_after": false
}
```

---

### Gestion Certificats

#### Demande Certificat PKCS#10
```bash
POST /soap/pkcs10Request
Content-Type: application/json

{
  "username": "testuser",
  "password": "secret123",
  "pkcs10": "-----BEGIN CERTIFICATE REQUEST-----\n...\n-----END CERTIFICATE REQUEST-----",
  "response_type": "CERTIFICATE"
}
```

#### Révoquer Certificat
```bash
POST /soap/revokeCert
Content-Type: application/json

{
  "issuer_dn": "CN=ManagementCA,O=EJBCA",
  "certificate_sn": "1234567890ABCDEF",
  "reason": 0
}
```

**Codes de révocation :**
| Code | Raison |
|------|--------|
| 0 | UNSPECIFIED |
| 1 | KEY_COMPROMISE |
| 2 | CA_COMPROMISE |
| 3 | AFFILIATION_CHANGED |
| 4 | SUPERSEDED |
| 5 | CESSATION_OF_OPERATION |
| 6 | CERTIFICATE_HOLD |

#### Trouver Certificats
```bash
POST /soap/findCerts
Content-Type: application/json

{
  "username": "testuser",
  "only_valid": true
}
```

#### Chaîne de Certificats
```bash
GET /soap/getLastCertChain?username=testuser
```

---

## 🐳 Docker Compose

### Services

| Service | Port | Description |
|---------|------|-------------|
| `mariadb` | 3307 | Base de données |
| `ejbca-ca` | 8080, 8443 | EJBCA CA (HTTP/HTTPS) |
| `fastapi-app` | 8000 | API Gateway |

### Commandes utiles

```bash
# Démarrer
docker compose up -d

# Logs
docker compose logs -f fastapi-app
docker compose logs -f ejbca-ca

# Redémarrer
docker compose restart fastapi-app

# Arrêter
docker compose down

# Tout supprimer (données incluses)
docker compose down -v
```

---

## 🔒 Sécurité

### Configuration SSL

L'API communique avec EJBCA via **HTTPS (port 8443)** avec authentification par certificat client.

Variables d'environnement :
```yaml
EJBCA_SOAP_URL: https://ejbca-ca:8443/ejbca/ejbcaws/ejbcaws
EJBCA_WSDL_URL: https://ejbca-ca:8443/ejbca/ejbcaws/ejbcaws?wsdl
EJBCA_CLIENT_CERT: /app/certs/soapadmin_cert.pem
EJBCA_CLIENT_KEY: /app/certs/soapadmin_key.pem
```

### Test manuel HTTPS

```bash
# Depuis le serveur
curl -k --cert ./certs/soapadmin_cert.pem \
        --key ./certs/soapadmin_key.pem \
        https://localhost:8443/ejbca/ejbcaws/ejbcaws?wsdl
```

---

## 📊 Opérations SOAP Disponibles (60 méthodes)

| Catégorie | Méthodes |
|-----------|----------|
| **CA** | `getAvailableCAs`, `getEjbcaVersion`, `createCA`, `createCRL` |
| **Utilisateurs** | `editUser`, `findUser`, `deleteUser`, `revokeUser` |
| **Certificats** | `pkcs10Request`, `certificateRequest`, `revokeCert`, `findCerts` |
| **Profils** | `getAvailableCertificateProfiles`, `getAuthorizedEndEntityProfiles` |
| **Crypto** | `createCryptoToken`, `generateKeys` |
| **SSH** | `enrollAndIssueSshCertificate` |
| **Autres** | `customLog`, `fetchUserData`, `checkRevokationStatus` |

---

## 🐛 Dépannage

### Le client SOAP ne se connecte pas

1. Vérifier que les certificats existent :
```bash
ls -la certs/
```

2. Vérifier les logs :
```bash
docker logs fastapi-app 2>&1 | grep -i error
```

3. Tester la connexion HTTPS :
```bash
docker exec fastapi-app curl -k https://ejbca-ca:8443/ejbca/ejbcaws/ejbcaws?wsdl
```

### Erreur "Connection reset by peer"

Le truststore EJBCA ne contient pas la CA. Relancer le script `setup-ssl.sh`.

### Certificat expiré

Régénérer le certificat admin :
```bash
docker exec ejbca-ca /opt/keyfactor/bin/ejbca.sh batch soapadmin
```

---

## 📁 Structure du Projet

```
ejbca-fastapi/
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration
│   ├── database.py         # Connexion DB
│   ├── dependencies.py     # Dépendances FastAPI
│   ├── main.py             # Point d'entrée
│   ├── models/             # Modèles SQLAlchemy
│   ├── routers/
│   │   └── soap_api.py     # Endpoints SOAP
│   ├── schemas/            # Schémas Pydantic
│   └── services/
│       └── ejbca_client.py # Client SOAP EJBCA
├── certs/                  # Certificats (généré)
├── deployment/
│   ├── deploy.sh           # Script déploiement
│   └── setup-ssl.sh        # Configuration SSL
├── docker-compose.yml
├── Dockerfile
├── init-db.sql
├── requirements.txt
└── README.md
```

---

## 📝 Licence

MIT License
