# # config.py
# import os

# from pydantic_settings import BaseSettings
# from typing import List, Optional

# class Settings(BaseSettings):
#     """Application settings"""
    
#     # API Settings
#     API_VERSION: str = "1.0.0"
#     API_TITLE: str = "Gluttex API"
#     API_DESCRIPTION: str = "API Documentation"
    
#     # Server Settings
#     HOST: str = "0.0.0.0"
#     PORT: int = 8000
#     DEBUG: str = os.getenv("ENV_MODE","DEV")
    
#     # CORS Settings
#     CORS_ORIGINS: List[str] = ["*"]
#     CORS_CREDENTIALS: bool = True
#     CORS_METHODS: List[str] = ["*"]
#     CORS_HEADERS: List[str] = ["*"]
    
#     # Session Settings
#     SESSION_SECRET_KEY: str = "your-secret-key-here"
#     SESSION_MAX_AGE: int = 3600
#     SESSION_SAME_SITE: str = "lax"
#     SESSION_HTTPS_ONLY: bool = False
    
#     # Database Settings
#     DATABASE_URL: Optional[str] = None
    
#     # Redis Settings (for caching)
#     REDIS_URL: Optional[str] = None

#     USE_VERSIONING: bool = True
#     TRUSTED_HOSTS: List[str] = ["*"]  # Override in production
#     CONTACT_EMAIL: Optional[str] = None
#     WORKERS: int = 1
    
    
#     class Config:
#         env_file = ".env"
#         case_sensitive = True

# settings = Settings()



