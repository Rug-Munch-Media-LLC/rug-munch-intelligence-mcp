"""
RMI Backend Settings
====================

Configuration for the FastAPI backend server.
Environment variables override defaults.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Backend configuration settings."""
    
    model_config = SettingsConfigDict(env_prefix="RMI_", env_file=".env", case_sensitive=True, extra="ignore")
    
    # Server settings
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8013)
    DEBUG: bool = Field(default=False)
    
    # Redis settings
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: str = Field(default="")
    
    # Allowed origins
    ALLOWED_ORIGINS: str = Field(default="*")
    
    # Version
    VERSION: str = Field(default="2.0.0")

    # Solana RPC URL
    SOLANA_RPC_URL: str = Field(default="https://api.mainnet-beta.solana.com")


# Global settings instance
settings = Settings()
