"""
Router principal avec endpoints généraux
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from datetime import datetime

from ..services.ejbca_client import ejbca_client_fixed

router = APIRouter(tags=["EJBCA Main"])
logger = logging.getLogger(__name__)

@router.get("/", summary="Root endpoint")
async def root() -> Dict[str, Any]:
    """Endpoint racine avec informations sur l'API EJBCA"""
    return {
        "api": "EJBCA SOAP API Gateway",
        "version": "2.0.0",
        "description": "Interface REST pour les services SOAP d'EJBCA",
        "documentation": "/docs",
        "endpoints": {
            "users": "/users",
            "certificates": "/certificates",
            "ca": "/ca",
            "profiles": "/profiles",
            "operations": "/operations",
            "system": "/system"
        }
    }

@router.get("/health", summary="Health check")
async def health_check() -> Dict[str, Any]:
    """Vérification de l'état de santé de l'API et d'EJBCA"""
    try:
        # Vérifier la connexion à EJBCA
        version = ejbca_client_fixed.get_version()
        
        return {
            "status": "healthy",
            "ejbca_connected": True,
            "ejbca_version": version,
            "api_status": "operational",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "degraded",
            "ejbca_connected": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/status/soap", summary="⭐ Vérifier la connexion SOAP")
async def check_soap_connection() -> Dict[str, Any]:
    """
    **Endpoint dédié pour vérifier la connexion SOAP à EJBCA**
    
    Retourne:
    - `connected`: True si connecté à EJBCA, False sinon
    - `ejbca_version`: Version d'EJBCA si connecté
    - `soap_endpoint`: URL du endpoint SOAP
    - `timestamp`: Heure de la vérification
    - `message`: Message descriptif du statut
    """
    try:
        # Test simple: obtenir la version EJBCA
        version = ejbca_client_fixed.get_version()
        
        if version and "EJBCA" in str(version):
            return {
                "connected": True,
                "message": "✅ Connecté à EJBCA via SOAP",
                "ejbca_version": version,
                "soap_endpoint": "https://ejbca-ca:8443/ejbca/ejbcaws/ejbcaws",
                "auth_method": "HTTP Basic Auth (superadmin:ejbca)",
                "soap_client": "Zeep (Python)",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "connected": False,
                "message": "❌ Pas de réponse valide d'EJBCA",
                "error": "Version non trouvée",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "connected": False,
            "message": "❌ Impossible de se connecter à EJBCA",
            "error": str(e),
            "soap_endpoint": "https://ejbca-ca:8443/ejbca/ejbcaws/ejbcaws",
            "troubleshooting": [
                "1. Vérifiez que les conteneurs Docker tournent: docker ps",
                "2. Vérifiez les logs EJBCA: docker logs ejbca-ca",
                "3. Vérifiez les logs API: docker logs ejbca-api",
                "4. Redémarrez les conteneurs: docker-compose restart"
            ],
            "timestamp": datetime.now().isoformat()
        }

@router.get("/status", summary="Status complet")
async def full_status() -> Dict[str, Any]:
    """Status complet du système avec métriques"""
    try:
        import psutil
        import os
        
        # Informations système
        system_info = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "process_memory_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        }
        
        # Informations EJBCA
        ejbca_info = {
            "connected": ejbca_client_fixed._initialized,
            "version": ejbca_client_fixed.get_version() if ejbca_client_fixed._initialized else None,
            "operations_count": len(ejbca_client_fixed._operations) if hasattr(ejbca_client_fixed, '_operations') else 0,
            "soap_endpoint": ejbca_client_fixed.soap_url
        }
        
        return {
            "system": system_info,
            "ejbca": ejbca_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
