"""
Client EJBCA avec authentification par certificat client
"""
import requests
from zeep import Client, Settings, Transport
import logging
import os
from typing import Dict, Any, Optional
import xml.etree.ElementTree as ET
import json
import urllib3

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class EJBCAClient:
    """Client EJBCA avec authentification par certificat client"""
    
    def __init__(self):
        # Configuration pour Docker
        self.wsdl_url = "https://ejbca-ca:8443/ejbca/ejbcaws/ejbcaws?wsdl"
        self.soap_url = "https://ejbca-ca:8443/ejbca/ejbcaws/ejbcaws"
        self.namespace = "http://ws.protocol.core.ejbca.org/"
        
        # Certificats pour l'authentification
        self.p12_file = "/app/certs/apiuser.p12"
        self.p12_password = "Marwa77233473"
        self.ca_file = "/app/certs/ca_cert.pem"
        
        self.client = None
        self._initialized = False
        self.ejbca_version = None
        self._operations = {}
        
    def initialize(self):
        """Initialise le client SOAP avec authentification par certificat"""
        try:
            print("\n" + "="*70)
            print("INITIALISATION CLIENT EJBCA AVEC CERTIFICAT CLIENT")
            print("="*70)
            
            # Vérifier le certificat P12
            print("1. Vérification du certificat P12...")
            if not os.path.exists(self.p12_file):
                print(f"   ❌ Certificat P12 manquant: {self.p12_file}")
                return False
            print(f"   ✅ Certificat P12 trouvé: {self.p12_file}")
            
            # Extraire le certificat et la clé du P12
            print("\n2. Extraction du certificat depuis P12...")
            from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
            
            with open(self.p12_file, 'rb') as f:
                p12_data = f.read()
            
            # Extraire certificat et clé
            private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                p12_data,
                self.p12_password.encode()
            )
            
            # Sauvegarder temporairement en PEM pour requests
            cert_pem_path = "/tmp/apiuser_cert.pem"
            key_pem_path = "/tmp/apiuser_key.pem"
            
            from cryptography.hazmat.primitives import serialization
            
            # Écrire le certificat
            with open(cert_pem_path, 'wb') as f:
                f.write(certificate.public_bytes(Encoding.PEM))
            
            # Écrire la clé privée
            with open(key_pem_path, 'wb') as f:
                f.write(private_key.private_bytes(
                    Encoding.PEM,
                    PrivateFormat.TraditionalOpenSSL,
                    NoEncryption()
                ))
            
            print(f"   ✅ Certificat extrait: {cert_pem_path}")
            print(f"   ✅ Clé extraite: {key_pem_path}")
            
            # Créer session avec certificat client UNIQUEMENT
            print("\n3. Configuration de la session HTTP avec certificat client...")
            session = requests.Session()
            session.cert = (cert_pem_path, key_pem_path)
            session.verify = False  # Désactiver vérification SSL pour self-signed cert
            print(f"   ✅ Session configurée avec certificat client")
            
            # Test de connexion WSDL
            print("\n3. Test d'accès au WSDL...")
            test_response = session.get(self.wsdl_url, timeout=10)
            if test_response.status_code == 200:
                print(f"   ✅ WSDL accessible (Status: {test_response.status_code})")
            else:
                print(f"   ❌ Erreur WSDL (Status: {test_response.status_code})")
                return False
            
            # Configuration Zeep
            print("\n4. Configuration du client SOAP...")
            settings = Settings(
                strict=False,
                xml_huge_tree=True,
                raw_response=False
            )
            
            transport = Transport(
                session=session,
                timeout=30,
                operation_timeout=30
            )
            
            # Créer le client Zeep
            print("\n5. Chargement du WSDL...")
            self.client = Client(
                wsdl=self.wsdl_url,
                transport=transport,
                settings=settings
            )
            print(f"   ✅ Client SOAP créé")
            
            # Extraire les opérations
            print("\n6. Extraction des opérations...")
            self._extract_operations()
            
            # Test avec getEjbcaVersion
            print("\n7. Test de connexion avec getEjbcaVersion...")
            version = self.client.service.getEjbcaVersion()
            
            if version:
                self.ejbca_version = version
                self._initialized = True
                print(f"   ✅ Version EJBCA: {version}")
                print(f"\n📊 {len(self._operations)} opérations disponibles")
                return True
            else:
                print("   ❌ Impossible de récupérer la version")
                return False
                
        except Exception as e:
            print(f"❌ Erreur initialisation: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _extract_operations(self):
        """Extrait les opérations du WSDL"""
        try:
            for service_name, service in self.client.wsdl.services.items():
                for port_name, port in service.ports.items():
                    if hasattr(port.binding, '_operations'):
                        for op_name in port.binding._operations.keys():
                            self._operations[op_name] = True
            
            # Sauvegarder
            with open("/tmp/ejbca_operations.json", "w") as f:
                json.dump(list(self._operations.keys()), f, indent=2)
                
            print(f"   ✅ {len(self._operations)} opérations trouvées")
        except Exception as e:
            print(f"   ⚠️  Erreur extraction: {e}")
            # Liste minimale d'opérations
            self._operations = {
                'getEjbcaVersion': True,
                'getAvailableCAs': True,
                'findUser': True,
                'editUser': True,
                'revokeCert': True,
                'getCertificate': True,
                'pkcs10Request': True,
                'revokeUser': True
            }
    
    def call_operation(self, operation_name, params=None):
        """Appelle une opération SOAP"""
        if not self._initialized:
            if not self.initialize():
                return {"error": "Client non initialisé"}
        
        params = params or {}
        
        try:
            # Essayer avec Zeep
            if hasattr(self.client.service, operation_name):
                method = getattr(self.client.service, operation_name)
                result = method(**params)
                return result
            else:
                print(f"⚠️  Opération {operation_name} non trouvée")
                return None
        except Exception as e:
            print(f"❌ Erreur {operation_name}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ========== MÉTHODES SPÉCIFIQUES ==========
    
    def get_version(self):
        """Version EJBCA"""
        return self.call_operation("getEjbcaVersion", {})
    
    def get_available_cas(self):
        """Liste des CAs"""
        return self.call_operation("getAvailableCAs", {})
    
    def find_user(self, username):
        """Recherche un utilisateur"""
        if not self._initialized:
            if not self.initialize():
                return None
        
        try:
            factory = self.client.type_factory('ns0')
            user_match = factory.userMatch(
                matchwith=0,  # USERNAME
                matchtype=0,  # EQUALS
                matchvalue=username
            )
            result = self.client.service.findUser(user_match)
            return result
        except Exception as e:
            print(f"❌ Erreur find_user: {e}")
            return None
    
    def find_users(self, match_with=0, match_type=0, match_value=""):
        """Recherche des utilisateurs avec critères"""
        if not self._initialized:
            if not self.initialize():
                return None
        
        try:
            factory = self.client.type_factory('ns0')
            user_match = factory.userMatch(
                matchwith=match_with,
                matchtype=match_type,
                matchvalue=match_value
            )
            result = self.client.service.findUser(user_match)
            return result
        except Exception as e:
            print(f"❌ Erreur find_users: {e}")
            return None
    
    def edit_user(self, user_data):
        """Crée ou modifie un utilisateur"""
        if not self._initialized:
            if not self.initialize():
                return None
        
        try:
            factory = self.client.type_factory('ns0')
            
            # Construire userDataVOWS avec tous les champs
            user_vo = factory.userDataVOWS(
                username=user_data.get('username'),
                password=user_data.get('password', ""),
                clearPwd=user_data.get('clearPwd', False),
                subjectDN=user_data.get('subjectDN', ""),
                caName=user_data.get('caName', "ManagementCA"),
                subjectAltName=user_data.get('subjectAltName', ""),
                email=user_data.get('email', ""),
                status=user_data.get('status', 10),  # NEW
                tokenType=user_data.get('tokenType', "USERGENERATED"),
                sendNotification=user_data.get('sendNotification', False),
                keyRecoverable=user_data.get('keyRecoverable', False),
                endEntityProfileName=user_data.get('endEntityProfileName', "EMPTY"),
                certificateProfileName=user_data.get('certificateProfileName', "ENDUSER")
            )
            
            result = self.client.service.editUser(user_vo)
            return result
        except Exception as e:
            print(f"❌ Erreur edit_user: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def revoke_cert(self, issuer_dn, certificate_sn, reason):
        """Révoque un certificat"""
        return self.call_operation("revokeCert", {
            'issuerDN': issuer_dn,
            'certificateSN': certificate_sn,
            'reason': reason
        })
    
    def get_certificate(self, issuer_dn, certificate_sn):
        """Récupère un certificat"""
        return self.call_operation("getCertificate", {
            'issuerDN': issuer_dn,
            'certificateSN': certificate_sn
        })
    
    def revoke_user(self, username):
        """Désactive un utilisateur"""
        return self.call_operation("revokeUser", {'username': username})
    
    def get_authorized_end_entity_profiles(self):
        """Profils d'entités finales"""
        return self.call_operation("getAuthorizedEndEntityProfiles", {})
    
    def get_available_certificate_profiles(self, end_entity_profile_name):
        """Profils de certificats"""
        return self.call_operation("getAvailableCertificateProfiles", {
            'endEntityProfileName': end_entity_profile_name
        })
    
    def pkcs10_request(self, username, password, pkcs10, hardtoken_sn=None, 
                       response_type=None, ca_name=None, end_entity_profile=None, 
                       certificate_profile=None, not_before=None, not_after=None):
        """Demande de certificat PKCS#10"""
        params = {
            'username': username,
            'password': password,
            'pkcs10': pkcs10
        }
        
        if hardtoken_sn:
            params['hardTokenSN'] = hardtoken_sn
        if response_type:
            params['responseType'] = response_type
        if ca_name:
            params['caName'] = ca_name
        if end_entity_profile:
            params['endEntityProfileName'] = end_entity_profile
        if certificate_profile:
            params['certificateProfileName'] = certificate_profile
        if not_before:
            params['notBefore'] = not_before
        if not_after:
            params['notAfter'] = not_after
            
        return self.call_operation("pkcs10Request", params)
    
    def get_last_ca_chain(self, ca_name):
        """Chaîne de certificats de la CA"""
        return self.call_operation("getLastCAChain", {'caName': ca_name})
    
    def get_latest_crl(self, ca_name, delta_crl=False):
        """Dernière CRL"""
        return self.call_operation("getLatestCRL", {
            'caName': ca_name,
            'deltaCRL': delta_crl
        })
    
    def get_all_operations(self):
        """Retourne la liste des opérations"""
        return list(self._operations.keys())


# Instance globale
ejbca_client_fixed = EJBCAClient()

def get_ejbca_client():
    """Retourne l'instance du client"""
    return ejbca_client_fixed
