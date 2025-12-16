"""
Router pour la gestion des Certificate Authorities (CA)
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import base64

from ..services.ejbca_client import ejbca_client_fixed

router = APIRouter(prefix="/ca", tags=["Certificate Authorities"])

class CreateCASchema(BaseModel):
    """Schéma pour créer une CA"""
    name: str
    subject_dn: str
    key_spec: Optional[str] = "2048"
    key_algorithm: Optional[str] = "RSA"
    validity_days: Optional[int] = 3650
    signed_by: Optional[int] = 0
    certificate_profile: Optional[str] = "ROOTCA"
    crypto_token: Optional[str] = "SoftCryptoToken"

@router.get("/", summary="Liste des CAs")
async def list_cas(
    active_only: bool = Query(True, description="CAs actives seulement")
) -> Dict[str, Any]:
    """Récupère la liste des Certificate Authorities disponibles"""
    try:
        cas = ejbca_client_fixed.get_available_cas()
        
        if active_only and cas:
            cas = [ca for ca in cas if "status" not in ca or ca.get("status") == "ACTIVE"]
        
        return {
            "cas": cas,
            "count": len(cas) if cas else 0,
            "active_only": active_only
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ca_name}", summary="Informations d'une CA")
async def get_ca_info(
    ca_name: str = Path(..., description="Nom de la CA")
) -> Dict[str, Any]:
    """Récupère les informations détaillées d'une CA"""
    try:
        chain = ejbca_client_fixed.get_last_ca_chain(ca_name)
        crl = ejbca_client_fixed.get_latest_crl(ca_name)
        
        return {
            "name": ca_name,
            "certificate_chain": chain,
            "crl": crl,
            "status": "ACTIVE",
            "certificates_issued": "N/A",
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ca_name}/chain", summary="Chaîne de certificats")
async def get_ca_chain(
    ca_name: str,
    format: str = Query("pem", regex="^(pem|der|base64)$")
) -> Dict[str, Any]:
    """Récupère la chaîne de certificats complète d'une CA"""
    try:
        chain = ejbca_client_fixed.get_last_ca_chain(ca_name)
        
        if format == "der":
            chain_der = base64.b64decode(chain) if chain else None
            return {
                "ca_name": ca_name,
                "chain": chain_der.hex() if chain_der else None,
                "format": "der"
            }
        elif format == "base64":
            return {
                "ca_name": ca_name,
                "chain": chain,
                "format": "base64"
            }
        else:
            return {
                "ca_name": ca_name,
                "chain": chain,
                "format": "pem"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ca_name}/crl", summary="CRL de la CA")
async def get_ca_crl(
    ca_name: str,
    delta: bool = Query(False, description="Récupérer la CRL delta"),
    format: str = Query("pem", regex="^(pem|der|base64)$")
) -> Dict[str, Any]:
    """Récupère la dernière Certificate Revocation List (CRL)"""
    try:
        crl = ejbca_client_fixed.get_latest_crl(ca_name, delta)
        
        if format == "der":
            crl_der = base64.b64decode(crl) if crl else None
            return {
                "ca_name": ca_name,
                "crl": crl_der.hex() if crl_der else None,
                "type": "delta" if delta else "base",
                "format": "der"
            }
        elif format == "base64":
            return {
                "ca_name": ca_name,
                "crl": crl,
                "type": "delta" if delta else "base",
                "format": "base64"
            }
        else:
            return {
                "ca_name": ca_name,
                "crl": crl,
                "type": "delta" if delta else "base",
                "format": "pem"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{ca_name}/crl/refresh", summary="Rafraîchir la CRL")
async def refresh_crl(
    ca_name: str,
    delta: bool = Query(False, description="Générer une CRL delta")
) -> Dict[str, Any]:
    """Force la génération d'une nouvelle CRL"""
    try:
        result = ejbca_client_fixed.call_operation("createCRL", {
            "caName": ca_name,
            "deltaCRL": delta
        })
        
        return {
            "success": True,
            "message": f"CRL {'delta ' if delta else ''}générée pour {ca_name}",
            "ca_name": ca_name,
            "delta": delta,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ca_name}/certificates", summary="Certificats émis par la CA")
async def get_ca_certificates(
    ca_name: str,
    status: Optional[str] = Query(None, regex="^(ACTIVE|REVOKED|EXPIRED|ALL)$"),
    days: Optional[int] = Query(None, ge=1, description="Certificats émis dans les X derniers jours"),
    limit: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """Récupère les certificats émis par une CA (avec filtres)"""
    try:
        result = ejbca_client_fixed.call_operation("findCerts", {
            "maxResults": limit,
            "issuerDN": f"CN={ca_name}",
            "status": status if status != "ALL" else "",
            "type": 0
        })
        
        return {
            "ca_name": ca_name,
            "certificates": result,
            "count": len(result) if result else 0,
            "filters": {
                "status": status,
                "days": days
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", summary="Créer une nouvelle CA", status_code=201)
async def create_ca(ca_data: CreateCASchema) -> Dict[str, Any]:
    """Crée une nouvelle Certificate Authority"""
    try:
        result = ejbca_client_fixed.call_operation("createCA", {
            "caName": ca_data.name,
            "subjectDN": ca_data.subject_dn,
            "keySpec": ca_data.key_spec or "2048",
            "keyAlgorithm": ca_data.key_algorithm or "RSA",
            "validity": ca_data.validity_days or 3650,
            "signedBy": ca_data.signed_by or 0,
            "certificateProfileName": ca_data.certificate_profile or "ROOTCA",
            "cryptoTokenName": ca_data.crypto_token or "SoftCryptoToken"
        })
        
        return {
            "success": True,
            "message": f"CA '{ca_data.name}' créée avec succès",
            "ca_name": ca_data.name,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ca_name}/stats", summary="Statistiques de la CA")
async def get_ca_statistics(
    ca_name: str,
    period_days: int = Query(30, ge=1, le=365, description="Période en jours")
) -> Dict[str, Any]:
    """Récupère les statistiques d'émission de certificats"""
    return {
        "ca_name": ca_name,
        "period_days": period_days,
        "statistics": {
            "total_certificates": "N/A",
            "active_certificates": "N/A",
            "revoked_certificates": "N/A",
            "expired_certificates": "N/A"
        },
        "note": "Les statistiques détaillées ne sont pas disponibles via l'API SOAP"
    }
