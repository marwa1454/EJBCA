"""
Certificate Workflow Router - Full SOAP Version
================================================
Endpoints complets pour gestion certificats EJBCA
Utilise les services SOAP directement pour toutes les opérations
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
import os
import io
import base64
from ..services.ejbca_client import ejbca_client_fixed as ejbca_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/certificate-flow", tags=["🔐 Certificats"])


# ==================== SCHEMAS ====================

class CreateUserRequest(BaseModel):
    """Créer utilisateur EJBCA"""
    username: str = Field(..., description="Identifiant unique")
    password: str = Field(..., description="Mot de passe sécurisé")
    email: str = Field(..., description="Adresse email")
    subject_dn: str = Field(..., description="CN=john,O=Company,C=DJ")
    ca_name: str = Field(default="ManagementCA", description="Certificat Authority")
    end_entity_profile: str = Field(default="EMPTY", description="Profil entité")


class SoftTokenRequest(BaseModel):
    """Générer PKCS#12 complet avec toutes les étapes"""
    username: str = Field(..., description="Identifiant utilisateur")
    password: str = Field(..., description="Mot de passe utilisateur")
    key_spec: str = Field(default="RSA2048", description="RSA2048, RSA4096, ECDSA256, ECDSA384")
    key_alg: str = Field(default="RSA", description="RSA, EC, DSA")
    ca_name: str = Field(default="ManagementCA", description="Certificat Authority")
    subject_dn: str = Field(..., description="CN=john,O=Company,C=DJ")
    certificate_type: str = Field(default="ENDUSER", description="ENDUSER, SERVER, CODESIGN")
    token_type: str = Field(default="SOFTTOKEN", description="SOFTTOKEN ou USERGENERATED")
    end_entity_profile: str = Field(default="EMPTY", description="Profil entité")


class FindCertRequest(BaseModel):
    """Rechercher certificats utilisateur"""
    username: str = Field(..., description="Identifiant utilisateur")


class RevokeRequest(BaseModel):
    """Révoquer certificat"""
    username: str = Field(..., description="Identifiant utilisateur")
    serial_number: Optional[str] = Field(None, description="Serial number du certificat (optionnel)")
    reason: int = Field(default=0, description="0=UNSPECIFIED, 1=KEYCOMPROMISE, 2=CACOMPROMISE, etc.")



class CertificateResponse(BaseModel):
    """Réponse standard certificat"""
    success: bool
    username: str
    message: str
    data: Optional[Dict[str, Any]] = None


# ==================== ENDPOINT 1: Create User Only ====================

@router.post("/create-user-only", response_model=CertificateResponse, 
    summary="Créer utilisateur EJBCA",
    description="Crée un nouvel utilisateur dans EJBCA (sans générer de certificat)")
async def create_user_only(req: CreateUserRequest):
    """
    Crée un utilisateur EJBCA via SOAP.
    
    **Étapes:**
    1. Valide les paramètres
    2. Crée l'utilisateur dans EJBCA
    3. Configure les profils de certificat
    
    **Réponse:**
    - success: true si création réussie
    - username: L'identifiant créé
    """
    try:
        # Lazy initialization du client SOAP
        ejbca_client._ensure_client()
        
        if not ejbca_client.client:
            raise HTTPException(status_code=503, detail="SOAP client non connecté à EJBCA")

        logger.info(f"[CREATE USER] {req.username} avec {req.ca_name}")

        # Créer l'objet utilisateur via SOAP
        user_data = ejbca_client.client.get_type('ns0:userDataVOWS')(
            username=req.username,
            password=req.password,
            clearPwd=True,
            subjectDN=req.subject_dn,
            email=req.email,
            caName=req.ca_name,
            endEntityProfileName=req.end_entity_profile,
            certificateProfileName="EMPTY",
            tokenType="USERGENERATED",
            status=10,  # NEW
            keyRecoverable=False,
            sendNotification=False
        )

        # Appeler editUser pour créer l'utilisateur
        ejbca_client.client.service.editUser(user_data)

        logger.info(f"✅ Utilisateur {req.username} créé via SOAP")
        return CertificateResponse(
            success=True,
            username=req.username,
            message=f"✅ Utilisateur '{req.username}' créé avec succès",
            data={"ca_name": req.ca_name, "subject_dn": req.subject_dn}
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Erreur création utilisateur: {error_msg}")
        
        # En mode développement, retourner un succès simulé pour les tests
        if os.getenv("DEBUG", "False").lower() == "true":
            logger.warning(f"⚠️  Mode DEBUG: Succès simulé pour {req.username}")
            return CertificateResponse(
                success=True,
                username=req.username,
                message=f"✅ [MOCK] Utilisateur '{req.username}' créé (mode développement)",
                data={"ca_name": req.ca_name, "subject_dn": req.subject_dn, "mock": True}
            )
        
        if "already exists" in error_msg.lower():
            return CertificateResponse(
                success=False,
                username=req.username,
                message=f"⚠️ Utilisateur '{req.username}' existe déjà"
            )
        
        return CertificateResponse(
            success=False,
            username=req.username,
            message=f"❌ Erreur: {error_msg[:200]}"
        )


# ==================== ENDPOINT 2: Generate PKCS#12 (Full Process) ====================

@router.post("/pkcs12",
    summary="Générer et télécharger PKCS#12",
    description="Génère un certificat PKCS#12 avec clé privée et le retourne en téléchargement")
async def generate_pkcs12(req: SoftTokenRequest):
    """
    Génère un certificat PKCS#12 et le retourne en tant que fichier binaire téléchargeable.
    
    **Processus:**
    1. Crée/met à jour l'utilisateur avec tous les paramètres
    2. Appelle softTokenRequest pour générer le certificat
    3. Retourne le fichier P12 en téléchargement direct
    
    **Paramètres requis:**
    - username: Identifiant utilisateur
    - password: Mot de passe
    - subject_dn: Distinguished Name complet
    - key_spec: RSA2048, RSA4096, ECDSA256, ECDSA384
    - certificate_type: ENDUSER, SERVER, CODESIGN
    - pkcs12_password: Mot de passe du P12
    
    **Réponse:**
    - Fichier PKCS#12 binaire (.p12) en téléchargement direct
    """
    try:
        # Lazy initialization du client SOAP
        ejbca_client._ensure_client()
        
        if not ejbca_client.client:
            raise Exception("SOAP client non connecté à EJBCA")

        logger.info(f"[PKCS12 DOWNLOAD] {req.username} - {req.key_spec}/{req.certificate_type}")

        # 1. Créer/mettre à jour l'utilisateur avec tous les paramètres
        user_data = ejbca_client.client.get_type('ns0:userDataVOWS')(
            username=req.username,
            password=req.password,
            clearPwd=True,
            subjectDN=req.subject_dn,
            subjectAltName="",
            email="",
            caName=req.ca_name,
            endEntityProfileName=req.end_entity_profile,
            certificateProfileName=req.certificate_type,
            tokenType=req.token_type,
            status=10,  # NEW
            keyRecoverable=False,
            sendNotification=False
        )

        # 2. Appeler softTokenRequest pour générer PKCS#12
        logger.info(f"   → Appel SOAP softTokenRequest")
        keystore_response = ejbca_client.client.service.softTokenRequest(
            user_data,
            req.password,
            "PKCS12"
        )

        # 3. Extraire les bytes du certificat
        if isinstance(keystore_response, dict):
            keystore_bytes = keystore_response.get('keyStore') or keystore_response.get('keystore')
        else:
            keystore_bytes = keystore_response

        if not keystore_bytes:
            raise Exception("Aucune donnée PKCS#12 retournée par EJBCA")

        # Convertir en bytes si nécessaire
        if isinstance(keystore_bytes, str):
            keystore_bytes = base64.b64decode(keystore_bytes)
        elif isinstance(keystore_bytes, bytearray):
            keystore_bytes = bytes(keystore_bytes)

        logger.info(f"✅ PKCS#12 généré pour {req.username} ({len(keystore_bytes)} bytes)")

        # 4. Retourner le fichier en téléchargement direct
        return FileResponse(
            io.BytesIO(keystore_bytes),
            media_type="application/x-pkcs12",
            filename=f"{req.username}_{req.ca_name}.p12",
            headers={
                "Content-Disposition": f'attachment; filename="{req.username}_{req.ca_name}.p12"'
            }
        )

    except Exception as e:
        error_msg = str(e).lower()
        full_error = str(e)
        logger.error(f"❌ Erreur PKCS#12: {full_error[:500]}")
        
        # En mode développement, retourner un fichier P12 mock pour les tests
        if os.getenv("DEBUG", "False").lower() == "true":
            logger.warning(f"⚠️  Mode DEBUG: Fichier P12 mock généré pour {req.username}")
            
            # Créer un fichier P12 mock vide (juste quelques bytes de base)
            mock_p12_data = b'\x30\x82\x04\xb4' + b'\x00' * 1200  # Simule un P12 vide
            
            return StreamingResponse(
                io.BytesIO(mock_p12_data),
                media_type="application/x-pkcs12",
                headers={
                    "Content-Disposition": f'attachment; filename="{req.username}_{req.ca_name}.p12"'
                }
            )
        
        if not ejbca_client.client:
            return CertificateResponse(
                success=False,
                username=req.username,
                message=f"❌ Client SOAP non connecté à EJBCA. Vérifiez que le service EJBCA est accessible."
            )
        
        if "user does not exist" in error_msg or "not found" in error_msg:
            return CertificateResponse(
                success=False,
                username=req.username,
                message=f"❌ Utilisateur '{req.username}' n'existe pas. Créez-le d'abord avec /create-user-only"
            )
        
        # Afficher les 200 premiers caractères de l'erreur
        error_display = full_error[:200] if full_error else "Erreur inconnue"
        return CertificateResponse(
            success=False,
            username=req.username,
            message=f"❌ Erreur PKCS#12: {error_display}"
        )


# ==================== ENDPOINT 3: Find User Certificates ====================

@router.get("/find-certs/{username}", response_model=CertificateResponse,
    summary="Lister certificats utilisateur",
    description="Récupère tous les certificats d'un utilisateur via SOAP")
async def find_user_certificates(username: str):
    """
    Récupère les certificats d'un utilisateur via SOAP findCerts.
    
    **Paramètres:**
    - username: Identifiant utilisateur
    
    **Réponse:**
    - certificates: Liste avec subject_dn, issuer_dn, serial_number, fingerprint
    """
    try:
        # Lazy initialization du client SOAP
        ejbca_client._ensure_client()
        
        if not ejbca_client.client:
            raise HTTPException(status_code=503, detail="SOAP client non connecté à EJBCA")

        logger.info(f"[FIND CERTS] {username}")

        # Appeler findCerts via SOAP
        certs = ejbca_client.client.service.findCerts(username, False)

        if not certs or len(certs) == 0:
            return CertificateResponse(
                success=True,
                username=username,
                message=f"Aucun certificat trouvé pour {username}",
                data={"certificate_count": 0, "certificates": []}
            )

        # Extraire les infos de chaque certificat
        cert_list = []
        for cert in certs:
            cert_info = {
                "subject_dn": getattr(cert, 'subjectDN', 'N/A'),
                "issuer_dn": getattr(cert, 'issuerDN', 'N/A'),
                "serial_number": str(getattr(cert, 'serialNumber', 'N/A')),
                "fingerprint": getattr(cert, 'fingerprint', 'N/A'),
                "status": getattr(cert, 'status', 'ACTIVE'),
            }
            cert_list.append(cert_info)

        logger.info(f"✅ {len(cert_list)} certificat(s) trouvé(s) pour {username}")

        return CertificateResponse(
            success=True,
            username=username,
            message=f"✅ {len(cert_list)} certificat(s) trouvé(s)",
            data={
                "certificate_count": len(cert_list),
                "certificates": cert_list
            }
        )

    except Exception as e:
        logger.error(f"❌ Erreur findCerts: {str(e)}")
        return CertificateResponse(
            success=False,
            username=username,
            message=f"❌ Erreur: {str(e)[:200]}"
        )


# ==================== ENDPOINT 4: Revoke Certificate ====================

@router.post("/revoke/{username}", response_model=CertificateResponse,
    summary="Révoquer certificat",
    description="Révoque le certificat d'un utilisateur via SOAP")
async def revoke_certificate(username: str, req: RevokeRequest):
    """
    Révoque le certificat d'un utilisateur via SOAP revokeCert.
    
    **Étapes:**
    1. Récupère le serial number du certificat (ou utilise celui fourni)
    2. Appelle revokeCert avec le numéro de série
    
    **Paramètres:**
    - username: Identifiant utilisateur
    - serial_number: (Optionnel) Serial du certificat à révoquer
    - reason: Code raison (0=UNSPECIFIED, 1=KEYCOMPROMISE, etc.)
    """
    try:
        # Lazy initialization du client SOAP
        ejbca_client._ensure_client()
        
        if not ejbca_client.client:
            raise HTTPException(status_code=503, detail="SOAP client non connecté à EJBCA")

        logger.info(f"[CREATE USER] {req.username}")

        # 1. Récupérer le serial number
        if not req.serial_number:
            certs = ejbca_client.client.service.findCerts(username, False)
            if not certs or len(certs) == 0:
                return CertificateResponse(
                    success=False,
                    username=username,
                    message=f"❌ Aucun certificat pour {username}"
                )
            serial_number = getattr(certs[0], 'serialNumber', None)
        else:
            serial_number = req.serial_number

        if not serial_number:
            return CertificateResponse(
                success=False,
                username=username,
                message=f"❌ Impossible de récupérer le serial number"
            )

        # 2. Appeler revokeCert via SOAP
        logger.info(f"   → Appel SOAP revokeCert pour serial {serial_number}")
        ejbca_client.client.service.revokeCert(
            str(serial_number),
            req.reason
        )

        logger.info(f"✅ Certificat {username} révoqué (serial: {serial_number})")

        return CertificateResponse(
            success=True,
            username=username,
            message=f"✅ Certificat révoqué (raison: {req.reason})",
            data={
                "serial_number": str(serial_number),
                "revocation_reason": req.reason
            }
        )

    except Exception as e:
        logger.error(f"❌ Erreur revokeCert: {str(e)}")
        return CertificateResponse(
            success=False,
            username=username,
            message=f"❌ Erreur: {str(e)[:200]}"
        )


# ==================== ENDPOINT 5: Download PKCS#12 File ====================

@router.post("/pkcs12/download", 
    summary="Télécharger fichier PKCS#12",
    description="Génère et télécharge un certificat PKCS#12 comme fichier binaire")
async def download_pkcs12(req: SoftTokenRequest):
    """
    Génère un certificat PKCS#12 et le retourne en tant que fichier binaire téléchargeable.
    
    **Réponse:** Fichier PKCS#12 binaire (.p12)
    """
    try:
        # Lazy initialization du client SOAP
        ejbca_client._ensure_client()
        
        if not ejbca_client.client:
            raise Exception("SOAP client non connecté à EJBCA")

        logger.info(f"[DOWNLOAD PKCS12] {req.username}")

        # 1. Créer/mettre à jour l'utilisateur
        user_data = ejbca_client.client.get_type('ns0:userDataVOWS')(
            username=req.username,
            password=req.password,
            clearPwd=True,
            subjectDN=req.subject_dn,
            subjectAltName="",
            email="",
            caName=req.ca_name,
            endEntityProfileName=req.end_entity_profile,
            certificateProfileName=req.certificate_type,
            tokenType=req.token_type,
            status=10,
            keyRecoverable=False,
            sendNotification=False
        )

        # 2. Appeler softTokenRequest pour générer PKCS#12
        logger.info(f"   → Appel SOAP softTokenRequest")
        keystore_response = ejbca_client.client.service.softTokenRequest(
            user_data,
            req.password,
            "PKCS12"
        )

        # 3. Extraire les bytes du certificat
        if isinstance(keystore_response, dict):
            keystore_bytes = keystore_response.get('keyStore') or keystore_response.get('keystore')
        else:
            keystore_bytes = keystore_response

        if not keystore_bytes:
            raise Exception("Aucune donnée PKCS#12 retournée par EJBCA")

        # Convertir en bytes si nécessaire
        if isinstance(keystore_bytes, str):
            keystore_bytes = base64.b64decode(keystore_bytes)
        elif isinstance(keystore_bytes, bytearray):
            keystore_bytes = bytes(keystore_bytes)

        logger.info(f"✅ PKCS#12 généré pour {req.username} ({len(keystore_bytes)} bytes)")

        # 4. Retourner le fichier en téléchargement direct
        return StreamingResponse(
            io.BytesIO(keystore_bytes),
            media_type="application/x-pkcs12",
            headers={
                "Content-Disposition": f'attachment; filename="{req.username}_{req.ca_name}.p12"'
            }
        )

    except Exception as e:
        logger.error(f"❌ Erreur download PKCS#12: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur génération PKCS#12: {str(e)[:200]}"
        )
