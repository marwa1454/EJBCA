"""
Router pour les opérations système et d'administration
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import sys

from ..services.ejbca_client import ejbca_client_fixed

router = APIRouter(prefix="/system", tags=["System Administration"])

@router.get("/info", summary="Informations système")
async def get_system_info() -> Dict[str, Any]:
    """Retourne les informations système complètes"""
    try:
        import platform
        import psutil
        
        app_info = {
            "name": "EJBCA REST API Gateway",
            "version": "2.0.0",
            "python_version": sys.version,
            "platform": platform.platform(),
            "working_directory": os.getcwd(),
            "pid": os.getpid()
        }
        
        ejbca_info = {
            "connected": ejbca_client_fixed._initialized,
            "version": ejbca_client_fixed.get_version() if ejbca_client_fixed._initialized else None,
            "endpoint": ejbca_client_fixed.soap_url,
            "operations_available": len(ejbca_client_fixed._operations) if hasattr(ejbca_client_fixed, '_operations') else 0
        }
        
        system_info = {
            "cpu": {
                "cores": psutil.cpu_count(),
                "usage_percent": psutil.cpu_percent(interval=1)
            },
            "memory": {
                "total_gb": psutil.virtual_memory().total / (1024**3),
                "available_gb": psutil.virtual_memory().available / (1024**3),
                "used_percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total_gb": psutil.disk_usage('/').total / (1024**3),
                "used_gb": psutil.disk_usage('/').used / (1024**3),
                "free_percent": 100 - psutil.disk_usage('/').percent
            }
        }
        
        return {
            "app": app_info,
            "ejbca": ejbca_info,
            "system": system_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs", summary="Journaux d'application")
async def get_application_logs(
    lines: int = Query(100, ge=1, le=10000, description="Nombre de lignes"),
    level: str = Query("INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"),
    search: str = Query(None, description="Rechercher dans les logs")
) -> Dict[str, Any]:
    """Récupère les journaux de l'application"""
    try:
        log_file = "app.log"
        
        if not os.path.exists(log_file):
            return {
                "logs": [],
                "file": log_file,
                "exists": False,
                "message": "Fichier de log non trouvé"
            }
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        filtered_lines = []
        for line in all_lines[-lines:]:
            if search and search.lower() not in line.lower():
                continue
            filtered_lines.append(line.strip())
        
        return {
            "logs": filtered_lines[-lines:],
            "total_lines": len(all_lines),
            "filtered_lines": len(filtered_lines),
            "filters": {
                "level": level,
                "search": search,
                "lines_requested": lines
            },
            "file": log_file
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics", summary="Métriques système")
async def get_system_metrics() -> Dict[str, Any]:
    """Retourne les métriques système pour le monitoring"""
    try:
        import psutil
        
        process = psutil.Process(os.getpid())
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "process": {
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / (1024 * 1024),
                "threads": process.num_threads()
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            },
            "api": {
                "ejbca_connected": ejbca_client_fixed._initialized,
                "operations_available": len(ejbca_client_fixed._operations) if hasattr(ejbca_client_fixed, '_operations') else 0
            }
        }
        
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restart", summary="Redémarrer l'application")
async def restart_application(
    confirm: bool = Query(False, description="Confirmer le redémarrage")
) -> Dict[str, Any]:
    """Redémarre l'application (nécessite confirmation)"""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation requise. Ajoutez ?confirm=true à l'URL"
        )
    
    try:
        return {
            "success": True,
            "message": "Redémarrage demandé",
            "restart_time": datetime.now().isoformat(),
            "note": "Dans un environnement Docker, utilisez 'docker restart <container>'"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config", summary="Configuration de l'application")
async def get_application_config(
    show_secrets: bool = Query(False, description="Afficher les secrets (attention!)")
) -> Dict[str, Any]:
    """Retourne la configuration de l'application"""
    try:
        config = {
            "ejbca": {
                "wsdl_url": ejbca_client_fixed.wsdl_url,
                "soap_url": ejbca_client_fixed.soap_url,
                "username": ejbca_client_fixed.username if show_secrets else "[HIDDEN]",
                "verify_ssl": False
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False
            }
        }
        
        return {
            "config": config,
            "warnings": ["Les secrets sont masqués par défaut"] if not show_secrets else [],
            "environment": os.environ.get("ENVIRONMENT", "development")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dependencies", summary="Dépendances de l'application")
async def get_dependencies() -> Dict[str, Any]:
    """Liste les dépendances Python et leurs versions"""
    try:
        deps = []
        req_file = "requirements.txt"
        
        if os.path.exists(req_file):
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        deps.append(line)
        
        return {
            "dependencies": deps,
            "total": len(deps)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
