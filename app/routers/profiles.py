"""
Router pour la gestion des profils EJBCA
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Dict, Any, Optional

from ..services.ejbca_client import ejbca_client_fixed

router = APIRouter(prefix="/profiles", tags=["Profiles Management"])

@router.get("/end-entity", summary="Profils d'entités finales")
async def list_end_entity_profiles(
    authorized_only: bool = Query(True, description="Profils autorisés seulement")
) -> Dict[str, Any]:
    """Liste les profils d'entités finales disponibles"""
    try:
        profiles = ejbca_client_fixed.get_authorized_end_entity_profiles()
        
        return {
            "profiles": profiles,
            "count": len(profiles) if profiles else 0,
            "type": "end_entity",
            "authorized_only": authorized_only
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/end-entity/{profile_name}", summary="Détails d'un profil d'entité finale")
async def get_end_entity_profile(
    profile_name: str = Path(..., description="Nom du profil")
) -> Dict[str, Any]:
    """Récupère les détails d'un profil d'entité finale"""
    try:
        profile = ejbca_client_fixed.call_operation("getProfile", {
            "profileType": "ENDENTITY",
            "profileName": profile_name
        })
        
        return {
            "name": profile_name,
            "type": "end_entity",
            "details": profile,
            "available_cas": ejbca_client_fixed.call_operation("getAvailableCAsInProfile", {
                "endEntityProfileName": profile_name
            }) if profile else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/certificate", summary="Profils de certificats")
async def list_certificate_profiles(
    end_entity_profile: Optional[str] = Query(None, description="Filtrer par profil d'entité finale")
) -> Dict[str, Any]:
    """Liste les profils de certificats disponibles"""
    try:
        if end_entity_profile:
            profiles = ejbca_client_fixed.get_available_certificate_profiles(end_entity_profile)
        else:
            profiles = []
            return {
                "profiles": [],
                "count": 0,
                "message": "Spécifiez un end_entity_profile pour voir les profils de certificats disponibles",
                "type": "certificate"
            }
        
        return {
            "profiles": profiles,
            "count": len(profiles) if profiles else 0,
            "end_entity_profile": end_entity_profile,
            "type": "certificate"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/certificate/{profile_name}", summary="Détails d'un profil de certificat")
async def get_certificate_profile(
    profile_name: str = Path(..., description="Nom du profil")
) -> Dict[str, Any]:
    """Récupère les détails d'un profil de certificat"""
    try:
        profile = ejbca_client_fixed.call_operation("getProfile", {
            "profileType": "CERTIFICATE",
            "profileName": profile_name
        })
        
        return {
            "name": profile_name,
            "type": "certificate",
            "details": profile,
            "key_usages": ["DIGITAL_SIGNATURE", "KEY_ENCIPHERMENT"],
            "extended_key_usages": ["SERVER_AUTH", "CLIENT_AUTH"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compatible", summary="Profils compatibles")
async def get_compatible_profiles(
    end_entity_profile: Optional[str] = Query(None, description="Profil d'entité finale"),
    certificate_profile: Optional[str] = Query(None, description="Profil de certificat")
) -> Dict[str, Any]:
    """Retourne les combinaisons de profils compatibles"""
    try:
        if end_entity_profile and certificate_profile:
            available = ejbca_client_fixed.get_available_certificate_profiles(end_entity_profile)
            compatible = any(
                (isinstance(p, dict) and p.get("name") == certificate_profile) or
                (isinstance(p, str) and p == certificate_profile)
                for p in (available or [])
            )
            return {
                "end_entity_profile": end_entity_profile,
                "certificate_profile": certificate_profile,
                "compatible": compatible,
                "type": "specific_check"
            }
        elif end_entity_profile:
            cert_profiles = ejbca_client_fixed.get_available_certificate_profiles(end_entity_profile)
            return {
                "end_entity_profile": end_entity_profile,
                "compatible_certificate_profiles": cert_profiles,
                "count": len(cert_profiles) if cert_profiles else 0,
                "type": "certificate_profiles_for_ee"
            }
        else:
            return {
                "combinations": [],
                "total_combinations": 0,
                "type": "all_combinations"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/types", summary="Types de profils disponibles")
async def get_profile_types() -> Dict[str, Any]:
    """Retourne les différents types de profils supportés"""
    return {
        "profile_types": [
            {
                "type": "ENDENTITY",
                "description": "Profil d'entité finale - définit les propriétés des utilisateurs",
                "endpoint": "/profiles/end-entity"
            },
            {
                "type": "CERTIFICATE", 
                "description": "Profil de certificat - définit les propriétés des certificats",
                "endpoint": "/profiles/certificate"
            },
            {
                "type": "HARDTOKEN",
                "description": "Profil de token matériel - pour les cartes à puce",
                "endpoint": "N/A"
            },
            {
                "type": "KEYRECOVERY",
                "description": "Profil de récupération de clé",
                "endpoint": "N/A"
            }
        ],
        "note": "Seuls ENDENTITY et CERTIFICATE sont pleinement supportés via SOAP"
    }

@router.get("/validation", summary="Validation de configuration")
async def validate_profile_configuration(
    end_entity_profile: str = Query(..., description="Profil d'entité finale"),
    certificate_profile: str = Query(..., description="Profil de certificat"),
    ca_name: str = Query(..., description="Nom de la CA")
) -> Dict[str, Any]:
    """Valide une configuration de profils pour la création de certificats"""
    try:
        ee_profiles = ejbca_client_fixed.get_authorized_end_entity_profiles()
        ee_exists = any(
            (isinstance(p, dict) and p.get("name") == end_entity_profile) or 
            (isinstance(p, str) and p == end_entity_profile)
            for p in (ee_profiles or [])
        )
        
        cert_profiles = ejbca_client_fixed.get_available_certificate_profiles(end_entity_profile)
        cert_compatible = any(
            (isinstance(p, dict) and p.get("name") == certificate_profile) or
            (isinstance(p, str) and p == certificate_profile)
            for p in (cert_profiles or [])
        )
        
        cas = ejbca_client_fixed.get_available_cas()
        ca_exists = any(
            (isinstance(ca, dict) and ca.get("name") == ca_name) or
            (isinstance(ca, str) and ca == ca_name)
            for ca in (cas or [])
        )
        
        return {
            "configuration": {
                "end_entity_profile": end_entity_profile,
                "certificate_profile": certificate_profile,
                "ca_name": ca_name
            },
            "validation": {
                "end_entity_profile_exists": ee_exists,
                "certificate_profile_compatible": cert_compatible,
                "ca_exists": ca_exists,
                "all_valid": ee_exists and cert_compatible and ca_exists
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
