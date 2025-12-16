"""
Certificate Generator - Génération locale de certificats PKCS#12
================================================================
Génère des certificats P12 en mode local sans passer par EJBCA SOAP
"""
import os
import base64
from pathlib import Path
from datetime import datetime
from typing import Tuple
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def generate_p12_certificate(
    username: str,
    subject_dn: str,
    pkcs12_password: str
) -> Tuple[bytes, str]:
    """
    Génère un certificat PKCS#12 valide et le sauvegarde localement.
    
    Args:
        username: Nom d'utilisateur (pour nommage du fichier)
        subject_dn: Distinguished Name complet (CN=...,O=...,C=...)
        pkcs12_password: Mot de passe pour chiffrer le P12
    
    Returns:
        Tuple contenant:
            - bytes du fichier P12
            - nom du fichier généré
    
    Example:
        p12_data, filename = generate_p12_certificate(
            username="alice",
            subject_dn="CN=Alice,O=ANSIE,C=DJ",
            pkcs12_password="secret123"
        )
    """
    try:
        logger.info(f"[CertGen] Génération P12 pour {username}")
        
        # 1. Parser le DN pour extraire le CN
        cn = _extract_cn_from_dn(subject_dn)
        
        # 2. Générer une clé privée RSA 2048 bits
        logger.debug(f"   → Génération clé RSA 2048")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # 3. Parser le DN pour créer les attributs X.509
        logger.debug(f"   → Création certificat avec DN: {subject_dn}")
        name_attributes = _parse_dn_to_x509_name(subject_dn)
        
        subject = issuer = x509.Name(name_attributes)
        
        # 4. Créer le certificat auto-signé
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
                x509.DNSName(cn if '.' in cn else f"{cn}.local"),
            ]),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).sign(
            private_key,
            hashes.SHA256(),
            default_backend()
        )
        
        logger.debug(f"   → Certificat créé (Serial: {cert.serial_number})")
        
        # 5. Créer le fichier PKCS#12
        logger.debug(f"   → Création PKCS#12 avec mot de passe")
        
        # Importer la dépendance pyOpenSSL
        try:
            from cryptography.hazmat.primitives.serialization import pkcs12
        except ImportError:
            logger.error("❌ Module cryptography.hazmat.primitives.serialization.pkcs12 non disponible")
            raise ImportError("Veuillez installer: pip install cryptography>=3.4")
        
        # Créer le PKCS#12
        p12_data = pkcs12.serialize_key_and_certificates(
            name=cn.encode() if isinstance(cn, str) else cn,
            key=private_key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(
                pkcs12_password.encode() if isinstance(pkcs12_password, str) else pkcs12_password
            )
        )
        
        logger.info(f"✅ PKCS#12 généré ({len(p12_data)} bytes)")
        
        # 6. Générer le nom du fichier
        filename = f"{username}_{cn}.p12"
        
        # 7. Retourner les données
        return p12_data, filename
        
    except Exception as e:
        logger.error(f"❌ Erreur génération certificat: {str(e)}")
        
        # En mode DEBUG, retourner un P12 mock (comme dans certificate_workflow.py)
        if os.getenv("DEBUG", "False").lower() == "true":
            logger.warning(f"⚠️  Mode DEBUG: Fichier P12 mock généré pour {username}")
            
            # Créer un fichier P12 mock vide (juste quelques bytes de base)
            mock_p12_data = b'\x30\x82\x04\xb4' + b'\x00' * 1200  # Simule un P12 vide
            filename = f"{username}_mock.p12"
            
            logger.debug(f"   → Mock P12 créé ({len(mock_p12_data)} bytes)")
            return mock_p12_data, filename
        else:
            raise


def _extract_cn_from_dn(dn: str) -> str:
    """
    Extrait le CN (Common Name) d'un DN.
    
    Example:
        "CN=Alice,O=ANSIE,C=DJ" -> "Alice"
    """
    parts = dn.split(',')
    for part in parts:
        part = part.strip()
        if part.startswith('CN='):
            return part[3:].strip()
    return "Unknown"


def _parse_dn_to_x509_name(dn: str) -> list:
    """
    Parse un DN (Distinguished Name) et le convertit en liste
    d'attributs X.509.
    
    Exemple:
        "CN=Alice,O=ANSIE,C=DJ" ->
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Alice"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ANSIE"),
            x509.NameAttribute(NameOID.COUNTRY_NAME, "DJ"),
        ]
    """
    # Mapping des attributs DN aux OIDs X.509
    oid_map = {
        'CN': NameOID.COMMON_NAME,
        'O': NameOID.ORGANIZATION_NAME,
        'OU': NameOID.ORGANIZATIONAL_UNIT_NAME,
        'C': NameOID.COUNTRY_NAME,
        'ST': NameOID.STATE_OR_PROVINCE_NAME,
        'L': NameOID.LOCALITY_NAME,
        'EMAIL': NameOID.EMAIL_ADDRESS,
    }
    
    attributes = []
    parts = dn.split(',')
    
    for part in parts:
        part = part.strip()
        if '=' not in part:
            continue
        
        key, value = part.split('=', 1)
        key = key.strip().upper()
        value = value.strip()
        
        if key in oid_map:
            attributes.append(
                x509.NameAttribute(oid_map[key], value)
            )
    
    return attributes
