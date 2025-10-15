from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    # MongoDB Settings
    MONGODB_URL: str
    DATABASE_NAME: str
    
    # JWT Settings
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # Stripe Settings
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLIC_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # CORS Settings
    CORS_ORIGINS: str = "*"
    
    # Email Settings
    MAIL_SERVER: str
    MAIL_PORT: int
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_FROM_NAME: str
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    
    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"  # Default value for development

    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_BOT_USERNAME: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None  # For production webhook mode

    # Tax Filing Service Settings
    TAX_RATE: float = 0.01  # 1% - Georgian small business tax (fixed by law)
    SERVICE_FEE_RATE: float = 0.02  # 2% - Our service fee for filing (configurable)
    # Total fee user pays = TAX_RATE + SERVICE_FEE_RATE = 3% of income

    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def TOTAL_FEE_RATE(self) -> float:
        """Total fee rate: tax + service fee"""
        return self.TAX_RATE + self.SERVICE_FEE_RATE

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()