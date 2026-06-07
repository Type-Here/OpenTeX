from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurazione applicazione caricata dall'ambiente / file .env."""

    mongo_uri: str
    mongo_db: str
    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
