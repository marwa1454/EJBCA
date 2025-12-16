"""
Router pour la gestion des utilisateurs EJBCA via SOAP Web Service
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
from zeep.helpers import serialize_object

from ..services.ejbca_client import ejbca_client_fixed

router = APIRouter(prefix="/users", tags=["Users Management"])


class UserCreate(BaseModel):
    """Schéma pour créer un utilisateur"""
    username: str
    password: str
    subjectDN: str
    caName: str = "ManagementCA"
    email: Optional[str] = ""
    subjectAltName: Optional[str] = ""
    tokenType: str = "USERGENERATED"
    endEntityProfileName: str = "EMPTY"
    certificateProfileName: str = "ENDUSER"
    clearPwd: bool = False
    keyRecoverable: bool = False
    sendNotification: bool = False


@router.get("/", summary="Lister les utilisateurs")
async def list_users() -> Dict[str, Any]:
    """
    Liste les utilisateurs EJBCA via SOAP Web Service.
    """
    try:
        # Note: EJBCA SOAP ne permet pas de lister tous les utilisateurs facilement
        # Il faut utiliser findUser avec des critères spécifiques
        return {
            "message": "Pour récupérer un utilisateur, utilisez GET /users/{username}",
            "hint": "EJBCA SOAP Web Service ne supporte pas la liste complète des utilisateurs"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{username}", summary="Récupérer un utilisateur")
async def get_user(username: str) -> Dict[str, Any]:
    """
    Recherche un utilisateur spécifique dans EJBCA.
    """
    try:
        user_data = ejbca_client_fixed.find_user(username)
        
        if not user_data:
            return {
                "found": False,
                "username": username,
                "message": f"Utilisateur '{username}' non trouvé"
            }
        
        # Convertir l'objet Zeep en dict pour la sérialisation JSON
        user_dict = serialize_object(user_data)
        
        return {
            "found": True,
            "username": username,
            "user_data": user_dict,
            "message": f"Utilisateur '{username}' trouvé"
        }
    except Exception as e:
        return {
            "found": False,
            "username": username,
            "error": str(e),
            "message": "Erreur lors de la recherche de l'utilisateur"
        }


@router.post("/", summary="Créer un utilisateur")
async def create_user(user_data: UserCreate) -> Dict[str, Any]:
    """
    Crée un nouvel utilisateur dans EJBCA.
    """
    try:
        ejbca_user_data = {
            "username": user_data.username,
            "password": user_data.password,
            "clearPwd": user_data.clearPwd,
            "subjectDN": user_data.subjectDN,
            "caName": user_data.caName,
            "email": user_data.email,
            "subjectAltName": user_data.subjectAltName or "",
            "keyRecoverable": user_data.keyRecoverable,
            "sendNotification": user_data.sendNotification,
            "tokenType": user_data.tokenType,
            "endEntityProfileName": user_data.endEntityProfileName,
            "certificateProfileName": user_data.certificateProfileName,
            "status": 10  # NEW
        }
        
        result = ejbca_client_fixed.edit_user(ejbca_user_data)
        
        return {
            "success": True,
            "message": f"Utilisateur '{user_data.username}' créé avec succès",
            "username": user_data.username,
            "result": result
        }
    except Exception as e:
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail=f"L'utilisateur '{user_data.username}' existe déjà"
            )
        raise HTTPException(status_code=500, detail=str(e))

