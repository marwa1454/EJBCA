# routers/ejbca.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any

from ..services.ejbca_client import get_ejbca_client

router = APIRouter(prefix="/ejbca", tags=["EJBCA"])

class UserData(BaseModel):
    username: str
    password: str
    subject_dn: str
    email: str
    ca_name: str = "IssuingCA"
    end_entity_profile: str = "EMPTY"
    certificate_profile: str = "ENDUSER"

@router.get("/test")
async def test_ejbca():
    """Test de connexion EJBCA"""
    client = get_ejbca_client()
    result = client.test_connection()
    return result

@router.get("/version")
async def get_ejbca_version():
    """Récupère la version d'EJBCA"""
    client = get_ejbca_client()
    version = client.get_version()
    return {"version": version}

@router.get("/cas")
async def get_cas():
    """Récupère la liste des CAs"""
    client = get_ejbca_client()
    cas = client.get_available_cas()
    return {"cas": cas}

@router.get("/profiles")
async def get_profiles():
    """Récupère les profils disponibles"""
    client = get_ejbca_client()
    profiles = client.get_authorized_profiles()
    return {"profiles": profiles}

@router.get("/users/{username}")
async def get_user(username: str):
    """Récupère les informations d'un utilisateur"""
    client = get_ejbca_client()
    user = client.find_user(username)
    return user

@router.post("/users")
async def create_user(user_data: UserData):
    """Crée un nouvel utilisateur"""
    client = get_ejbca_client()
    result = client.create_end_entity(user_data.dict())
    return result

@router.post("/certificates/revoke")
async def revoke_certificate(serial_number: str, reason: int = 0):
    """Révoque un certificat"""
    client = get_ejbca_client()
    result = client.revoke_certificate(serial_number, reason)
    return result

@router.get("/certificates/{serial_number}")
async def get_certificate(serial_number: str, issuer_dn: str = ""):
    """Récupère un certificat"""
    client = get_ejbca_client()
    result = client.get_certificate(serial_number, issuer_dn)
    return result

@router.get("/status")
async def ejbca_status():
    """Statut complet d'EJBCA"""
    client = get_ejbca_client()
    
    status = {
        "connected": client._initialized,
        "version": client.get_version(),
        "service_url": client.soap_url,
    }
    
    if client._initialized:
        status.update({
            "cas": client.get_available_cas(),
            "profiles": client.get_authorized_profiles(),
        })
    
    return status
