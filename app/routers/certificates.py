"""
Router pour la gestion des certificats
"""
from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import base64
import os
import tempfile
from cryptography.hazmat.primitives.serialization import pkcs12, NoEncryption
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from ..services.ejbca_client import ejbca_client_fixed

router = APIRouter(prefix="/certificates", tags=["Certificates Management"])

class PKCS10RequestSchema(BaseModel):
    """Schéma pour une demande PKCS#10"""
    username: str
    password: str
    pkcs10_data: str
    ca_name: Optional[str] = None
    end_entity_profile: Optional[str] = None
    certificate_profile: Optional[str] = None
    not_before: Optional[str] = None
    not_after: Optional[str] = None

class CRMFCertRequestSchema(BaseModel):
    """Schéma pour une demande CRMF"""
    username: str
    password: str
    crmf_data: str
    ca_name: Optional[str] = None
    end_entity_profile: Optional[str] = None
    certificate_profile: Optional[str] = None

class RevokeCertificateSchema(BaseModel):
    """Schéma pour révoquer un certificat"""
    serial_number: str
    issuer_dn: str
    reason: int = Field(0, ge=0, le=10)

class RenewCertificateSchema(BaseModel):
    """Schéma pour renouveler un certificat"""
    serial_number: str
    issuer_dn: str

class GenerateCSRSchema(BaseModel):
    """Schéma pour générer un CSR"""
    username: str
    common_name: Optional[str] = None
    organization: str = "ANSIE"
    country: str = "DJ"
    email: Optional[str] = None
    ca_name: str = "IssuingCA"
    end_entity_profile: str = "EMPTY"
    certificate_profile: str = "ENDUSER"

@router.get("/", summary="Recherche de certificats")
async def search_certificates(
    issuer_dn: Optional[str] = Query(None, description="DN de l'émetteur"),
    subject_dn: Optional[str] = Query(None, description="DN du sujet"),
    username: Optional[str] = Query(None, description="Nom d'utilisateur"),
    serial_number: Optional[str] = Query(None, description="Numéro de série"),
    status: Optional[str] = Query(None, description="Statut (ACTIVE, REVOKED, etc)"),
    limit: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """Recherche de certificats avec filtres multiples"""
    try:
        result = ejbca_client_fixed.call_operation("findCerts", {
            "maxResults": limit,
            "issuerDN": issuer_dn or "",
            "subjectDN": subject_dn or "",
            "username": username or "",
            "status": status or "",
            "serialNumber": serial_number or "",
            "type": 0
        })
        
        return {
            "certificates": result,
            "count": len(result) if result else 0,
            "filters": {
                "issuer_dn": issuer_dn,
                "subject_dn": subject_dn,
                "username": username,
                "serial_number": serial_number,
                "status": status
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{serial_number}", summary="Récupérer un certificat")
async def get_certificate(
    serial_number: str = Path(..., description="Numéro de série hexadécimal"),
    issuer_dn: Optional[str] = Query(None, description="DN de l'émetteur")
) -> Dict[str, Any]:
    """Récupère un certificat par son numéro de série"""
    try:
        cert = ejbca_client_fixed.get_certificate(
            issuer_dn or "",
            serial_number
        )
        
        if not cert:
            raise HTTPException(
                status_code=404,
                detail=f"Certificat {serial_number} non trouvé"
            )
        
        return {
            "certificate": cert,
            "serial_number": serial_number,
            "formats": {
                "pem": cert.get("certificate"),
                "der": base64.b64decode(cert.get("certificate", "")).hex() if cert.get("certificate") else None
            }
        }
    except Exception as e:
        if "Certificate could not be found" in str(e):
            raise HTTPException(status_code=404, detail=f"Certificat {serial_number} non trouvé")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/request/pkcs10", summary="Demande PKCS#10", status_code=201)
async def request_pkcs10_certificate(request: PKCS10RequestSchema) -> Dict[str, Any]:
    """Soumet une demande de certificat PKCS#10"""
    try:
        result = ejbca_client_fixed.pkcs10_request(
            username=request.username,
            password=request.password,
            pkcs10=request.pkcs10_data,
            ca_name=request.ca_name,
            end_entity_profile=request.end_entity_profile,
            certificate_profile=request.certificate_profile,
            not_before=request.not_before,
            not_after=request.not_after
        )
        
        return {
            "success": True,
            "message": "Demande de certificat soumise avec succès",
            "certificate": result,
            "format": "PKCS#10"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/request/crmf", summary="Demande CRMF")
async def request_crmf_certificate(request: CRMFCertRequestSchema) -> Dict[str, Any]:
    """Soumet une demande de certificat CRMF"""
    try:
        result = ejbca_client_fixed.crmf_request(
            username=request.username,
            password=request.password,
            crmf=request.crmf_data,
            ca_name=request.ca_name,
            end_entity_profile=request.end_entity_profile,
            certificate_profile=request.certificate_profile
        )
        
        return {
            "success": True,
            "message": "Demande CRMF soumise avec succès",
            "certificate": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/revoke", summary="Révoquer un certificat")
async def revoke_certificate(request: RevokeCertificateSchema) -> Dict[str, Any]:
    """Révoque un certificat"""
    try:
        result = ejbca_client_fixed.revoke_cert(
            issuer_dn=request.issuer_dn,
            certificate_sn=request.serial_number,
            reason=request.reason
        )
        
        return {
            "success": True,
            "message": f"Certificat {request.serial_number} révoqué",
            "reason": request.reason,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/revoke/batch", summary="Révocation par lot")
async def batch_revoke_certificates(requests: List[RevokeCertificateSchema]) -> Dict[str, Any]:
    """Révoque plusieurs certificats en une seule requête"""
    results = []
    
    for request in requests:
        try:
            result = ejbca_client_fixed.revoke_cert(
                issuer_dn=request.issuer_dn,
                certificate_sn=request.serial_number,
                reason=request.reason
            )
            results.append({
                "serial_number": request.serial_number,
                "success": True,
                "result": result
            })
        except Exception as e:
            results.append({
                "serial_number": request.serial_number,
                "success": False,
                "error": str(e)
            })
    
    success_count = sum(1 for r in results if r["success"])
    
    return {
        "total": len(results),
        "success": success_count,
        "failed": len(results) - success_count,
        "results": results
    }

@router.get("/{serial_number}/status", summary="Statut d'un certificat")
async def get_certificate_status(
    serial_number: str,
    issuer_dn: Optional[str] = Query(None, description="DN de l'émetteur")
) -> Dict[str, Any]:
    """Vérifie le statut de révocation d'un certificat"""
    try:
        result = ejbca_client_fixed.call_operation("checkRevokationStatus", {
            "issuerDN": issuer_dn or "",
            "certificateSN": serial_number
        })
        
        return {
            "serial_number": serial_number,
            "status": result,
            "is_revoked": result != "NOT_REVOKED"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/expiring", summary="Certificats expirant bientôt")
async def get_expiring_certificates(
    days: int = Query(30, ge=1, le=365, description="Jours avant expiration"),
    limit: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """Récupère les certificats expirant dans les X jours"""
    try:
        expiration_date = datetime.now() + timedelta(days=days)
        expiration_timestamp = int(expiration_date.timestamp() * 1000)
        
        result = ejbca_client_fixed.call_operation("getCertificatesByExpirationTime", {
            "maxResults": limit,
            "expireBeforeDate": expiration_timestamp
        })
        
        return {
            "certificates": result,
            "count": len(result) if result else 0,
            "expiration_window_days": days,
            "expiration_before": expiration_date.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/renew", summary="Renouveler un certificat")
async def renew_certificate(request: RenewCertificateSchema) -> Dict[str, Any]:
    """Renouvelle un certificat expiré ou bientôt expiré"""
    try:
        old_cert = ejbca_client_fixed.get_certificate(
            request.issuer_dn,
            request.serial_number
        )
        
        if not old_cert:
            raise HTTPException(status_code=404, detail="Certificat non trouvé")
        
        return {
            "success": True,
            "message": "Renouvellement initié",
            "old_serial": request.serial_number,
            "note": "Le renouvellement nécessite une nouvelle paire de clés"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{serial_number}/download/pem", summary="Télécharger le certificat en PEM")
async def download_certificate_pem(
    serial_number: str = Path(..., description="Numéro de série du certificat"),
    format: str = Query("pem", regex="^(pem|der|base64)$", description="Format: pem, der ou base64")
):
    """
    Télécharge le certificat dans le format demandé.
    - PEM: Format texte lisible
    - DER: Format binaire compressé
    - Base64: PEM encodé en base64
    """
    try:
        # Récupérer le certificat
        cert_result = ejbca_client_fixed.call_operation(
            'getCertificate',
            {'certSN': serial_number}
        )
        
        if not cert_result or 'error' in cert_result:
            raise HTTPException(status_code=404, detail="Certificat non trouvé")
        
        # Extraire le certificat
        cert_data = cert_result.get('return', {})
        cert_bytes = base64.b64decode(cert_data.get('certificate', ''))
        
        if format == "der":
            return FileResponse(
                content=cert_bytes,
                media_type="application/octet-stream",
                filename=f"{serial_number}.der"
            )
        elif format == "base64":
            cert_b64 = base64.b64encode(cert_bytes).decode()
            return {
                "serial_number": serial_number,
                "format": "base64",
                "certificate": cert_b64
            }
        else:  # PEM
            cert_pem = cert_bytes.decode('utf-8')
            return FileResponse(
                content=cert_pem.encode(),
                media_type="application/octet-stream",
                filename=f"{serial_number}.pem"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{serial_number}/download/p12", summary="Télécharger le certificat en P12 (PKCS#12)")
async def download_certificate_p12(
    serial_number: str = Path(..., description="Numéro de série du certificat"),
    private_key_path: str = Query(..., description="Chemin vers la clé privée PEM (ex: marwa_complete_key.pem)"),
    password: str = Query("1234", description="Mot de passe pour protéger le P12")
):
    """
    Crée un fichier PKCS#12 (.p12) contenant:
    - Le certificat X.509
    - La clé privée (à partir du fichier fourni)
    
    Le fichier P12 peut être importé dans les navigateurs, clients VPN, etc.
    
    **Parameters:**
    - serial_number: Numéro de série du certificat à télécharger
    - private_key_path: Chemin vers la clé privée (ex: marwa_complete_key.pem)
    - password: Mot de passe pour protéger le P12 (défaut: 1234)
    """
    try:
        # Vérifier que le fichier de clé existe
        if not os.path.exists(private_key_path):
            raise HTTPException(
                status_code=400, 
                detail=f"Fichier de clé privée non trouvé: {private_key_path}"
            )
        
        # Récupérer le certificat
        cert_result = ejbca_client_fixed.call_operation(
            'getCertificate',
            {'certSN': serial_number}
        )
        
        if not cert_result or 'error' in cert_result:
            raise HTTPException(status_code=404, detail="Certificat non trouvé")
        
        # Charger le certificat
        cert_data = cert_result.get('return', {})
        cert_bytes = base64.b64decode(cert_data.get('certificate', ''))
        cert = x509.load_der_x509_certificate(cert_bytes, default_backend())
        
        # Charger la clé privée
        with open(private_key_path, 'rb') as f:
            key_pem = f.read()
        private_key = serialization.load_pem_private_key(
            key_pem,
            password=None,
            backend=default_backend()
        )
        
        # Créer le fichier P12
        p12_data = pkcs12.serialize_key_and_certificates(
            name=serial_number.encode(),
            key=private_key,
            cert=cert,
            cas=None,  # Sans CA intermédiaire
            encryption_algorithm=serialization.BestAvailableEncryption(password.encode())
        )
        
        # Sauvegarder temporairement
        with tempfile.NamedTemporaryFile(suffix='.p12', delete=False) as tmp:
            tmp.write(p12_data)
            tmp_path = tmp.name
        
        return FileResponse(
            path=tmp_path,
            media_type="application/octet-stream",
            filename=f"{serial_number}.p12",
            headers={
                "Content-Disposition": f'attachment; filename="{serial_number}.p12"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{serial_number}/download/p12/test", summary="⭐ Télécharger P12 de TEST (auto-signé)")
async def download_certificate_p12_test(
    serial_number: str = Path(..., description="Numéro de série ou nom pour le certificat"),
    password: str = Query("1234", description="Mot de passe pour protéger le P12")
):
    """
    **ENDPOINT DE DÉMONSTRATION**: Crée un P12 auto-signé pour test.
    
    Utile pour tester le téléchargement P12 immédiatement sans attendre un certificat EJBCA réel.
    Génère un certificat de test avec la clé privée marwa_complete_key.pem.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import hashes
        from datetime import datetime, timedelta
        
        # Charger ou générer la clé privée
        key_path = "marwa_complete_key.pem"
        
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                key_pem = f.read()
            private_key = serialization.load_pem_private_key(
                key_pem,
                password=None,
                backend=default_backend()
            )
        else:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
        
        # Créer un certificat auto-signé de test
        subject = issuer = x509.Name([
            x509.NameAttribute(x509.oid.NameOID.COUNTRY_NAME, u"DJ"),
            x509.NameAttribute(x509.oid.NameOID.ORGANIZATION_NAME, u"ANSIE"),
            x509.NameAttribute(x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME, u"IT"),
            x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, u"Marwa Complete (TEST)"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.RFC822Name(u"marwa.complete@ansie.dj"),
                x509.DNSName(u"marwa.ansie.dj"),
            ]),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).sign(
            private_key, hashes.SHA256(), backend=default_backend()
        )
        
        # Créer le fichier P12
        p12_data = pkcs12.serialize_key_and_certificates(
            name=serial_number.encode(),
            key=private_key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(password.encode())
        )
        
        # Sauvegarder temporairement
        with tempfile.NamedTemporaryFile(suffix='.p12', delete=False) as tmp:
            tmp.write(p12_data)
            tmp_path = tmp.name
        
        return FileResponse(
            path=tmp_path,
            media_type="application/octet-stream",
            filename=f"{serial_number}_test.p12",
            headers={
                "Content-Disposition": f'attachment; filename="{serial_number}_test.p12"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-csr", summary="⭐ Générer clé privée + CSR automatiquement", response_model=Dict)
async def generate_csr(request: GenerateCSRSchema):
    """
    **ENDPOINT AUTOMATISÉ**: Génère une clé privée RSA + CSR en une seule requête!
    
    Retourne:
    - La clé privée (PEM)
    - Le CSR en base64 (prêt pour la demande de certificat)
    - Un JSON complet pour soumettre immédiatement à `/certificates/request/pkcs10`
    
    **Étapes:**
    1. Générer une clé RSA 2048 bits
    2. Créer le CSR avec vos données
    3. Encoder en base64
    4. Retourner le JSON prêt à l'emploi
    
    Exemple d'utilisation:
    ```bash
    curl -X POST http://localhost:8000/certificates/generate-csr \\
      -H "Content-Type: application/json" \\
      -d '{
        "username": "marwa_complete",
        "common_name": "Marwa Complete",
        "email": "marwa.complete@ansie.dj"
      }'
    ```
    """
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import hashes
        import json
        
        # 1. Générer la clé privée RSA 2048
        print(f"🔑 Génération de la clé RSA pour {request.username}...")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Convertir en PEM
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        # 2. Créer le CSR
        print(f"📝 Création du CSR...")
        common_name = request.common_name or request.username
        
        subject = x509.Name([
            x509.NameAttribute(x509.oid.NameOID.COUNTRY_NAME, request.country),
            x509.NameAttribute(x509.oid.NameOID.ORGANIZATION_NAME, request.organization),
            x509.NameAttribute(x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME, u"IT"),
            x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, common_name),
        ])
        
        # Extensions SAN (Subject Alternative Name)
        san_list = []
        if request.email:
            san_list.append(x509.RFC822Name(request.email))
            san_list.append(x509.DNSName(request.email.split('@')[1]))
        else:
            san_list.append(x509.DNSName(f"{request.username}.ansie.dj"))
        
        csr = x509.CertificateSigningRequestBuilder().subject_name(
            subject
        ).add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Convertir en PEM
        csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()
        
        # 3. Encoder en base64
        print(f"🔐 Encodage en base64...")
        pkcs10_data = base64.b64encode(csr_pem.encode()).decode()
        
        # 4. Créer le JSON prêt à l'emploi pour /certificates/request/pkcs10
        pkcs10_request = {
            "username": request.username,
            "password": "ChangeMe@123",
            "pkcs10_data": pkcs10_data,
            "ca_name": request.ca_name,
            "end_entity_profile": request.end_entity_profile,
            "certificate_profile": request.certificate_profile
        }
        
        return {
            "success": True,
            "message": f"CSR généré avec succès pour {request.username}",
            "username": request.username,
            "private_key": key_pem,
            "csr_pem": csr_pem,
            "pkcs10_data": pkcs10_data,
            "next_step": "Utilisez le JSON ci-dessous pour POST /certificates/request/pkcs10",
            "pkcs10_request_json": pkcs10_request
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))