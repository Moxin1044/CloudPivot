from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "CloudPivot"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str = "change-me-to-a-random-secret-key"
    APP_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    APP_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://cloudpivot:cloudpivot@localhost:5432/cloudpivot"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # SMTP
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 465
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    # WebSSH
    WEBSSH_SSH_TIMEOUT: int = 30
    WEBSSH_MAX_SESSIONS_PER_USER: int = 5

    # Agent
    AGENT_SECRET_KEY: str = "agent-secret-key-change-me"

    # Docker
    DOCKER_HOST: str = "unix:///var/run/docker.sock"

    # Logging
    LOG_LEVEL: str = "INFO"

    # CAPTCHA
    CAPTCHA_ENABLED: bool = True
    CAPTCHA_EXPIRE_SECONDS: int = 300

    # Login Security
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Default admin
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"
    DEFAULT_ADMIN_EMAIL: str = "admin@cloudpivot.localhost"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
