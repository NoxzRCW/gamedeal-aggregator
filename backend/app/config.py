from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    itad_api_key: str = ""
    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = 900
    cors_origins: str = "*"

    class Config:
        env_file = ".env"


settings = Settings()
