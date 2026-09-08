from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_secret: str = ""

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = ""
    ollama_embed_model: str = ""

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    neo4j_uri: str = ""
    neo4j_user: str = ""
    neo4j_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
