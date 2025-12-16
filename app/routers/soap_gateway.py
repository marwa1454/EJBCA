"""
SOAP Gateway - Expose tous les 60 endpoints EJBCA SOAP
======================================================
Connexion directe aux services SOAP d'EJBCA avec authentification par certificat
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Any, Dict, Optional
import logging
from app.services.ejbca_client import EJBCAClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/soap", tags=["EJBCA SOAP Gateway"])

# Initialiser le client SOAP
soap_client = EJBCAClient()

# Tous les 60 endpoints EJBCA SOAP
SOAP_ENDPOINTS = [
    "addSubjectToRole",
    "caCertResponse",
    "caCertResponseForRollover",
    "caRenewCertRequest",
    "certificateRequest",
    "checkRevokationStatus",
    "createCA",
    "createCRL",
    "createCryptoToken",
    "createExternallySignedCa",
    "crmfRequest",
    "customLog",
    "cvcRequest",
    "deleteUserDataFromSource",
    "editUser",
    "enrollAndIssueSshCertificate",
    "existsHardToken",
    "fetchUserData",
    "findCerts",
    "findUser",
    "generateCryptoTokenKeys",
    "genTokenCertificates",
    "getAuthorizedEndEntityProfiles",
    "getAvailableCAs",
    "getAvailableCAsInProfile",
    "getAvailableCertificateProfiles",
    "getCertificate",
    "getCertificatesByExpirationTime",
    "getCertificatesByExpirationTimeAndIssuer",
    "getCertificatesByExpirationTimeAndType",
    "getEjbcaVersion",
    "getHardTokenData",
    "getHardTokenDatas",
    "getLastCAChain",
    "getLastCertChain",
    "getLatestCRL",
    "getLatestCRLPartition",
    "getProfile",
    "getPublisherQueueLength",
    "getRemainingNumberOfApprovals",
    "getSshCaPublicKey",
    "importCaCert",
    "isApproved",
    "isAuthorized",
    "keyRecover",
    "keyRecoverEnroll",
    "keyRecoverNewest",
    "pkcs10Request",
    "pkcs12Req",
    "removeSubjectFromRole",
    "republishCertificate",
    "revokeCert",
    "revokeCertBackdated",
    "revokeCertWithMetadata",
    "revokeToken",
    "revokeUser",
    "rolloverCACert",
    "softTokenRequest",
    "spkacRequest",
]

@router.get("/status")
async def soap_status():
    """Vérifier l'état de la connexion SOAP"""
    client = soap_client.get_client()
    return {
        "connected": client is not None,
        "endpoints_available": len(SOAP_ENDPOINTS),
        "endpoints": SOAP_ENDPOINTS
    }

@router.post("/init")
async def soap_init():
    """Forcer l'initialisation de la connexion SOAP"""
    try:
        client = soap_client.get_client()
        if client is None:
            raise Exception("Impossible de se connecter à EJBCA SOAP")
        
        # Tenter un appel simple pour vérifier
        version = client.service.getEjbcaVersion()
        return {
            "success": True,
            "message": "✅ SOAP connecté avec succès",
            "version": str(version),
            "endpoints_count": len(SOAP_ENDPOINTS)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)[:200],
            "endpoints_count": len(SOAP_ENDPOINTS)
        }

@router.post("/call/{operation_name}")
async def call_soap_operation(operation_name: str, params: Dict[str, Any] = Body(...)):
    """
    Appeler un opération SOAP EJBCA
    
    Parameters:
    - operation_name: Nom de l'opération SOAP (ex: getAvailableCAs)
    - params: Dictionnaire des paramètres pour l'opération
    
    Example:
    POST /soap/call/getAvailableCAs
    {
        "caName": "ManagementCA"
    }
    """
    if operation_name not in SOAP_ENDPOINTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown operation '{operation_name}'. Available: {SOAP_ENDPOINTS}"
        )
    
    try:
        client = soap_client.get_client()
        if not client:
            raise HTTPException(status_code=503, detail="SOAP client not initialized")
        
        # Appeler la méthode dynamiquement
        service = client.service
        method = getattr(service, operation_name, None)
        
        if not method:
            raise HTTPException(status_code=400, detail=f"Operation {operation_name} not found")
        
        # Appeler avec les paramètres
        result = method(**params)
        
        logger.info(f"✅ SOAP Operation: {operation_name} - SUCCESS")
        return {
            "operation": operation_name,
            "success": True,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"❌ SOAP Operation: {operation_name} - ERROR: {str(e)[:200]}")
        raise HTTPException(status_code=500, detail=f"SOAP Error: {str(e)[:200]}")

# Créer des routes spécifiques pour chaque endpoint (pour Swagger documentation)
@router.post("/addSubjectToRole")
async def soap_addSubjectToRole(params: Dict[str, Any] = Body(...)):
    """Add a subject to a role in EJBCA"""
    return await call_soap_operation("addSubjectToRole", params)

@router.post("/getAvailableCAs")
async def soap_getAvailableCAs(params: Dict[str, Any] = Body(...)):
    """Get all available CAs in EJBCA"""
    return await call_soap_operation("getAvailableCAs", params)

@router.post("/getCertificate")
async def soap_getCertificate(params: Dict[str, Any] = Body(...)):
    """Get a certificate from EJBCA"""
    return await call_soap_operation("getCertificate", params)

@router.post("/getEjbcaVersion")
async def soap_getEjbcaVersion(params: Dict[str, Any] = Body(default={})):
    """Get EJBCA version"""
    return await call_soap_operation("getEjbcaVersion", params if params else {})

@router.post("/pkcs12Req")
async def soap_pkcs12Req(params: Dict[str, Any] = Body(...)):
    """Create a PKCS#12 certificate request"""
    return await call_soap_operation("pkcs12Req", params)

@router.post("/pkcs10Request")
async def soap_pkcs10Request(params: Dict[str, Any] = Body(...)):
    """Create a PKCS#10 certificate request"""
    return await call_soap_operation("pkcs10Request", params)

@router.post("/certificateRequest")
async def soap_certificateRequest(params: Dict[str, Any] = Body(...)):
    """Create a certificate request"""
    return await call_soap_operation("certificateRequest", params)

@router.post("/findUser")
async def soap_findUser(params: Dict[str, Any] = Body(...)):
    """Find a user in EJBCA"""
    return await call_soap_operation("findUser", params)

@router.post("/editUser")
async def soap_editUser(params: Dict[str, Any] = Body(...)):
    """Edit a user in EJBCA"""
    return await call_soap_operation("editUser", params)

@router.post("/findCerts")
async def soap_findCerts(params: Dict[str, Any] = Body(...)):
    """Find certificates in EJBCA"""
    return await call_soap_operation("findCerts", params)

@router.post("/revokeCert")
async def soap_revokeCert(params: Dict[str, Any] = Body(...)):
    """Revoke a certificate"""
    return await call_soap_operation("revokeCert", params)

@router.post("/revokeUser")
async def soap_revokeUser(params: Dict[str, Any] = Body(...)):
    """Revoke a user"""
    return await call_soap_operation("revokeUser", params)

@router.post("/checkRevokationStatus")
async def soap_checkRevokationStatus(params: Dict[str, Any] = Body(...)):
    """Check revocation status of a certificate"""
    return await call_soap_operation("checkRevokationStatus", params)

@router.post("/createCA")
async def soap_createCA(params: Dict[str, Any] = Body(...)):
    """Create a new CA"""
    return await call_soap_operation("createCA", params)

@router.post("/getAvailableCertificateProfiles")
async def soap_getAvailableCertificateProfiles(params: Dict[str, Any] = Body(...)):
    """Get available certificate profiles"""
    return await call_soap_operation("getAvailableCertificateProfiles", params)

@router.post("/getAvailableCAsInProfile")
async def soap_getAvailableCAsInProfile(params: Dict[str, Any] = Body(...)):
    """Get available CAs in a profile"""
    return await call_soap_operation("getAvailableCAsInProfile", params)

@router.post("/getAuthorizedEndEntityProfiles")
async def soap_getAuthorizedEndEntityProfiles(params: Dict[str, Any] = Body(...)):
    """Get authorized end entity profiles"""
    return await call_soap_operation("getAuthorizedEndEntityProfiles", params)

@router.post("/softTokenRequest")
async def soap_softTokenRequest(params: Dict[str, Any] = Body(...)):
    """Create a soft token request"""
    return await call_soap_operation("softTokenRequest", params)

@router.post("/crmfRequest")
async def soap_crmfRequest(params: Dict[str, Any] = Body(...)):
    """Create a CRMF request"""
    return await call_soap_operation("crmfRequest", params)

@router.post("/spkacRequest")
async def soap_spkacRequest(params: Dict[str, Any] = Body(...)):
    """Create a SPKAC request"""
    return await call_soap_operation("spkacRequest", params)

@router.post("/cvcRequest")
async def soap_cvcRequest(params: Dict[str, Any] = Body(...)):
    """Create a CVC request"""
    return await call_soap_operation("cvcRequest", params)

@router.post("/enrollAndIssueSshCertificate")
async def soap_enrollAndIssueSshCertificate(params: Dict[str, Any] = Body(...)):
    """Enroll and issue SSH certificate"""
    return await call_soap_operation("enrollAndIssueSshCertificate", params)

@router.post("/getSshCaPublicKey")
async def soap_getSshCaPublicKey(params: Dict[str, Any] = Body(...)):
    """Get SSH CA public key"""
    return await call_soap_operation("getSshCaPublicKey", params)

@router.post("/fetchUserData")
async def soap_fetchUserData(params: Dict[str, Any] = Body(...)):
    """Fetch user data"""
    return await call_soap_operation("fetchUserData", params)

@router.post("/deleteUserDataFromSource")
async def soap_deleteUserDataFromSource(params: Dict[str, Any] = Body(...)):
    """Delete user data from source"""
    return await call_soap_operation("deleteUserDataFromSource", params)

@router.post("/getLastCAChain")
async def soap_getLastCAChain(params: Dict[str, Any] = Body(...)):
    """Get last CA chain"""
    return await call_soap_operation("getLastCAChain", params)

@router.post("/getLastCertChain")
async def soap_getLastCertChain(params: Dict[str, Any] = Body(...)):
    """Get last certificate chain"""
    return await call_soap_operation("getLastCertChain", params)

@router.post("/getLatestCRL")
async def soap_getLatestCRL(params: Dict[str, Any] = Body(...)):
    """Get latest CRL"""
    return await call_soap_operation("getLatestCRL", params)

@router.post("/getLatestCRLPartition")
async def soap_getLatestCRLPartition(params: Dict[str, Any] = Body(...)):
    """Get latest CRL partition"""
    return await call_soap_operation("getLatestCRLPartition", params)

@router.post("/createCRL")
async def soap_createCRL(params: Dict[str, Any] = Body(...)):
    """Create a CRL"""
    return await call_soap_operation("createCRL", params)

@router.post("/createCryptoToken")
async def soap_createCryptoToken(params: Dict[str, Any] = Body(...)):
    """Create a crypto token"""
    return await call_soap_operation("createCryptoToken", params)

@router.post("/generateCryptoTokenKeys")
async def soap_generateCryptoTokenKeys(params: Dict[str, Any] = Body(...)):
    """Generate crypto token keys"""
    return await call_soap_operation("generateCryptoTokenKeys", params)

@router.post("/genTokenCertificates")
async def soap_genTokenCertificates(params: Dict[str, Any] = Body(...)):
    """Generate token certificates"""
    return await call_soap_operation("genTokenCertificates", params)

@router.post("/keyRecover")
async def soap_keyRecover(params: Dict[str, Any] = Body(...)):
    """Key recovery"""
    return await call_soap_operation("keyRecover", params)

@router.post("/keyRecoverEnroll")
async def soap_keyRecoverEnroll(params: Dict[str, Any] = Body(...)):
    """Key recover enroll"""
    return await call_soap_operation("keyRecoverEnroll", params)

@router.post("/keyRecoverNewest")
async def soap_keyRecoverNewest(params: Dict[str, Any] = Body(...)):
    """Key recover newest"""
    return await call_soap_operation("keyRecoverNewest", params)

@router.post("/republishCertificate")
async def soap_republishCertificate(params: Dict[str, Any] = Body(...)):
    """Republish certificate"""
    return await call_soap_operation("republishCertificate", params)

@router.post("/revokeCertBackdated")
async def soap_revokeCertBackdated(params: Dict[str, Any] = Body(...)):
    """Revoke certificate with backdate"""
    return await call_soap_operation("revokeCertBackdated", params)

@router.post("/revokeCertWithMetadata")
async def soap_revokeCertWithMetadata(params: Dict[str, Any] = Body(...)):
    """Revoke certificate with metadata"""
    return await call_soap_operation("revokeCertWithMetadata", params)

@router.post("/revokeToken")
async def soap_revokeToken(params: Dict[str, Any] = Body(...)):
    """Revoke token"""
    return await call_soap_operation("revokeToken", params)

@router.post("/caRenewCertRequest")
async def soap_caRenewCertRequest(params: Dict[str, Any] = Body(...)):
    """CA renew certificate request"""
    return await call_soap_operation("caRenewCertRequest", params)

@router.post("/rolloverCACert")
async def soap_rolloverCACert(params: Dict[str, Any] = Body(...)):
    """Rollover CA certificate"""
    return await call_soap_operation("rolloverCACert", params)

@router.post("/caCertResponse")
async def soap_caCertResponse(params: Dict[str, Any] = Body(...)):
    """CA certificate response"""
    return await call_soap_operation("caCertResponse", params)

@router.post("/caCertResponseForRollover")
async def soap_caCertResponseForRollover(params: Dict[str, Any] = Body(...)):
    """CA certificate response for rollover"""
    return await call_soap_operation("caCertResponseForRollover", params)

@router.post("/createExternallySignedCa")
async def soap_createExternallySignedCa(params: Dict[str, Any] = Body(...)):
    """Create externally signed CA"""
    return await call_soap_operation("createExternallySignedCa", params)

@router.post("/importCaCert")
async def soap_importCaCert(params: Dict[str, Any] = Body(...)):
    """Import CA certificate"""
    return await call_soap_operation("importCaCert", params)

@router.post("/isApproved")
async def soap_isApproved(params: Dict[str, Any] = Body(...)):
    """Check if approved"""
    return await call_soap_operation("isApproved", params)

@router.post("/isAuthorized")
async def soap_isAuthorized(params: Dict[str, Any] = Body(...)):
    """Check if authorized"""
    return await call_soap_operation("isAuthorized", params)

@router.post("/addSubjectToRole")
async def soap_addSubjectToRole_2(params: Dict[str, Any] = Body(...)):
    """Add subject to role"""
    return await call_soap_operation("addSubjectToRole", params)

@router.post("/removeSubjectFromRole")
async def soap_removeSubjectFromRole(params: Dict[str, Any] = Body(...)):
    """Remove subject from role"""
    return await call_soap_operation("removeSubjectFromRole", params)

@router.post("/getProfile")
async def soap_getProfile(params: Dict[str, Any] = Body(...)):
    """Get profile"""
    return await call_soap_operation("getProfile", params)

@router.post("/getPublisherQueueLength")
async def soap_getPublisherQueueLength(params: Dict[str, Any] = Body(...)):
    """Get publisher queue length"""
    return await call_soap_operation("getPublisherQueueLength", params)

@router.post("/getRemainingNumberOfApprovals")
async def soap_getRemainingNumberOfApprovals(params: Dict[str, Any] = Body(...)):
    """Get remaining number of approvals"""
    return await call_soap_operation("getRemainingNumberOfApprovals", params)

@router.post("/existsHardToken")
async def soap_existsHardToken(params: Dict[str, Any] = Body(...)):
    """Check if hard token exists"""
    return await call_soap_operation("existsHardToken", params)

@router.post("/getHardTokenData")
async def soap_getHardTokenData(params: Dict[str, Any] = Body(...)):
    """Get hard token data"""
    return await call_soap_operation("getHardTokenData", params)

@router.post("/getHardTokenDatas")
async def soap_getHardTokenDatas(params: Dict[str, Any] = Body(...)):
    """Get hard tokens data"""
    return await call_soap_operation("getHardTokenDatas", params)

@router.post("/customLog")
async def soap_customLog(params: Dict[str, Any] = Body(...)):
    """Custom log"""
    return await call_soap_operation("customLog", params)

@router.post("/getCertificatesByExpirationTime")
async def soap_getCertificatesByExpirationTime(params: Dict[str, Any] = Body(...)):
    """Get certificates by expiration time"""
    return await call_soap_operation("getCertificatesByExpirationTime", params)

@router.post("/getCertificatesByExpirationTimeAndIssuer")
async def soap_getCertificatesByExpirationTimeAndIssuer(params: Dict[str, Any] = Body(...)):
    """Get certificates by expiration time and issuer"""
    return await call_soap_operation("getCertificatesByExpirationTimeAndIssuer", params)

@router.post("/getCertificatesByExpirationTimeAndType")
async def soap_getCertificatesByExpirationTimeAndType(params: Dict[str, Any] = Body(...)):
    """Get certificates by expiration time and type"""
    return await call_soap_operation("getCertificatesByExpirationTimeAndType", params)
