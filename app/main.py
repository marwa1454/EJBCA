"""
Application FastAPI principale - API REST Gateway pour EJBCA
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

from .routers import all_routers
from .services.ejbca_client import ejbca_client_fixed

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Création de l'application FastAPI
app = FastAPI(
    title="EJBCA REST API Gateway",
    description="Interface REST complète pour les services SOAP d'EJBCA",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure tous les routeurs
for router in all_routers:
    app.include_router(router)

# Événements de démarrage/arrêt
@app.on_event("startup")
async def startup_event():
    """Exécuté au démarrage de l'application"""
    logger.info("Démarrage de l'API EJBCA...")
    
    # Initialiser le client EJBCA
    try:
        if ejbca_client_fixed.initialize():
            logger.info("✅ Client EJBCA initialisé avec succès")
        else:
            logger.error("❌ Échec d'initialisation du client EJBCA")
    except Exception as e:
        logger.error(f"❌ Erreur d'initialisation EJBCA: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Exécuté à l'arrêt de l'application"""
    logger.info("Arrêt de l'API EJBCA...")

# Endpoint de test basique
@app.get("/")
async def root():
    return {
        "message": "EJBCA REST API Gateway",
        "version": "2.0.0",
        "docs": "/docs",
        "endpoints": {
            "users": "/users",
            "certificates": "/certificates",
            "ca": "/ca",
            "profiles": "/profiles",
            "operations": "/operations",
            "system": "/system"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
