# app/config.py
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl

class Settings(BaseSettings):
    so_topic: str
    rabbitmq_host: str
    rabbitmq_port: int
    host: str = "0.0.0.0"
    port: int = 8080

    class Config:
        env_prefix = ""
        case_sensitive = False

settings = Settings()
