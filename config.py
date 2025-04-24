from pydantic_settings import BaseSettings
from datetime import datetime, time
from typing import Dict, ClassVar, Any

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "sqlite:///./tson-queue.db"
    
    # JWT settings
    JWT_SECRET_KEY: str = "your-secret-key-here"  # In production, use environment variable
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Business hours
    OPENING_TIME: time = time(9, 0)  # 9:00 AM
    CLOSING_TIME: time = time(18, 0)  # 6:00 PM
    
    # Admin credentials
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "password"  # In production, use hashed password
    
    # Timezone configuration
    TIMEZONE_NAME: str = "Asia/Almaty"  # Almaty/Astana timezone
    WORKING_HOURS: Dict[str, int] = {
        "start": 9,  # 9 AM
        "end": 18    # 6 PM (exclusive)
    }
    SLOT_DURATION_MINUTES: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings()