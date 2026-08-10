"""Application configuration."""
import os
from typing import Optional

class Config:
    """Configuration class."""
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM = "HS256"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///app.db")
    
    # JWT
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CORS
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:8080"
    ).split(",")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration."""
        if len(cls.SECRET_KEY) < 32:
            logger.warning("SECRET_KEY should be at least 32 characters")
        return True

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG: bool = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG: bool = False

class TestingConfig(Config):
    """Testing configuration."""
    TESTING: bool = True
    DATABASE_URL: str = ":memory:"

# Configuration factory
def get_config(env: Optional[str] = None) -> Config:
    """Get configuration based on environment."""
    if env == "production":
        return ProductionConfig()
    elif env == "testing":
        return TestingConfig()
    return DevelopmentConfig()
