"""
Configuration centralisée depuis les variables d'environnement
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # === Database ===
    mariadb_host: str = os.getenv("MARIADB_HOST", "localhost")
    mariadb_port: int = int(os.getenv("MARIADB_PORT", "3306"))
    mariadb_user: str = os.getenv("MARIADB_USER", "root")
    mariadb_password: str = os.getenv("MARIADB_PASSWORD", "")
    mariadb_database: str = os.getenv("MARIADB_DATABASE", "ejbca_fastapi")
    
    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.mariadb_user}:{self.mariadb_password}@{self.mariadb_host}:{self.mariadb_port}/{self.mariadb_database}"
    
    # === API ===
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    
    # === SOAP ===
    ejbca_host: str = os.getenv("EJBCA_HOST", "localhost")
    ejbca_port: str = os.getenv("EJBCA_PORT", "8443")
    ejbca_protocol: str = os.getenv("EJBCA_PROTOCOL", "https")
    ejbca_client_cert: str = os.getenv("EJBCA_CLIENT_CERT", "")
    ejbca_client_key: str = os.getenv("EJBCA_CLIENT_KEY", "")
    
    # === Debug ===
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignorer les variables env non définies
    
    @property
    def ejbca_soap_url(self) -> str:
        return f"{self.ejbca_protocol}://{self.ejbca_host}:{self.ejbca_port}/ejbca/ejbcaws/ejbcaws"
    
    @property
    def ejbca_wsdl_url(self) -> str:
        return f"{self.ejbca_protocol}://{self.ejbca_host}:{self.ejbca_port}/ejbca/ejbcaws/ejbcaws?wsdl"


# Instance unique de settings
settings = Settings()