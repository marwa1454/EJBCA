"""
Router pour les opérations SOAP génériques et avancées
"""
from fastapi import APIRouter, HTTPException, Query, Path, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json

from ..services.ejbca_client import ejbca_client_fixed

router = APIRouter(prefix="/operations", tags=["SOAP Operations"])

class GenericOperationRequest(BaseModel):
    """Requête pour une opération SOAP générique"""
    operation: str = Field(..., description="Nom de l'opération SOAP")
    params: Dict[str, Any] = Field(default_factory=dict, description="Paramètres de l'opération")
    validate_only: bool = Field(False, description="Valider seulement, ne pas exécuter")

@router.get("/", summary="Liste des opérations disponibles")
async def list_operations(
    category: Optional[str] = Query(None, description="Filtrer par catégorie"),
    search: Optional[str] = Query(None, description="Recherche par nom")
) -> Dict[str, Any]:
    """Liste toutes les opérations SOAP disponibles avec filtrage"""
    try:
        all_ops = ejbca_client_fixed.get_all_operations()
        
        if category:
            filtered_ops = [op for op in all_ops if category.lower() in op.lower()]
        else:
            filtered_ops = all_ops
        
        if search:
            filtered_ops = [op for op in filtered_ops if search.lower() in op.lower()]
        
        return {
            "operations": filtered_ops,
            "total": len(filtered_ops),
            "filters": {
                "category": category,
                "search": search
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{operation_name}", summary="Détails d'une opération")
async def get_operation_details(
    operation_name: str = Path(..., description="Nom de l'opération SOAP")
) -> Dict[str, Any]:
    """Récupère les détails d'une opération SOAP spécifique"""
    try:
        info = ejbca_client_fixed.get_operation_info(operation_name)
        
        if not info:
            all_ops = ejbca_client_fixed.get_all_operations()
            if operation_name not in all_ops:
                raise HTTPException(status_code=404, detail=f"Opération '{operation_name}' non trouvée")
            
            info = {"name": operation_name, "status": "exists_but_no_details"}
        
        return {
            "operation": operation_name,
            "details": info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute", summary="Exécuter une opération")
async def execute_operation(
    request: GenericOperationRequest,
    dry_run: bool = Query(False, description="Simuler l'exécution sans réel appel")
) -> Dict[str, Any]:
    """Exécute une opération SOAP générique"""
    try:
        all_ops = ejbca_client_fixed.get_all_operations()
        if request.operation not in all_ops:
            raise HTTPException(
                status_code=404,
                detail=f"Opération '{request.operation}' non trouvée"
            )
        
        if request.validate_only or dry_run:
            return {
                "operation": request.operation,
                "params": request.params,
                "validated": True,
                "dry_run": dry_run,
                "message": "Opération validée avec succès"
            }
        
        result = ejbca_client_fixed.call_operation(
            request.operation,
            request.params
        )
        
        return {
            "operation": request.operation,
            "params": request.params,
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "operation": request.operation,
            "params": request.params,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/batch", summary="Exécution par lot")
async def execute_batch_operations(
    requests: List[GenericOperationRequest],
    stop_on_error: bool = Query(True, description="Arrêter à la première erreur")
) -> Dict[str, Any]:
    """Exécute plusieurs opérations SOAP en une seule requête"""
    results = []
    successful = 0
    failed = 0
    
    for i, request in enumerate(requests):
        try:
            if stop_on_error and failed > 0:
                results.append({
                    "index": i,
                    "operation": request.operation,
                    "status": "skipped",
                    "reason": "Previous operation failed"
                })
                continue
            
            result = ejbca_client_fixed.call_operation(
                request.operation,
                request.params
            )
            
            results.append({
                "index": i,
                "operation": request.operation,
                "status": "success",
                "result": result
            })
            successful += 1
            
        except Exception as e:
            results.append({
                "index": i,
                "operation": request.operation,
                "status": "error",
                "error": str(e)
            })
            failed += 1
    
    return {
        "total": len(requests),
        "successful": successful,
        "failed": failed,
        "stop_on_error": stop_on_error,
        "results": results
    }

@router.get("/test/simple", summary="Test des opérations simples")
async def test_simple_operations() -> Dict[str, Any]:
    """Teste les opérations simples (sans paramètres)"""
    try:
        test_results = ejbca_client_fixed.test_all_operations()
        
        return {
            "tests": test_results,
            "summary": {
                "total_tested": len(test_results),
                "successful": sum(1 for r in test_results.values() if r.get("success")),
                "failed": sum(1 for r in test_results.values() if not r.get("success"))
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
