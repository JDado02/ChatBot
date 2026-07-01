"""
Configurazione del backend, letta da variabili d'ambiente (con default per
lo sviluppo locale coerenti con .env.example / docker-compose.yml).

Volutamente senza pydantic per ora: dipendenze minime. La validazione più
strutturata arriverà con FastAPI al Passo 6.
"""
from __future__ import annotations

import os


class Settings:
    def __init__(self) -> None:
        # --- Database (il backend si connette come ruolo NON-superuser app_user,
        # così la Row-Level Security è sempre applicata) ---
        self.db_host: str = os.getenv("DB_HOST", "localhost")
        self.db_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
        self.db_name: str = os.getenv("POSTGRES_DB", "concierge")
        self.db_user: str = os.getenv("APP_DB_USER", "app_user")
        self.db_password: str = os.getenv("APP_DB_PASSWORD", "app_dev_only")

        # --- Modelli locali (dev via Ollama) ---
        self.ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "bge-m3")
        self.embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "1024"))
        self.chat_model: str = os.getenv("CHAT_MODEL", "llama3")

        # --- Redis (memoria conversazioni) ---
        self.redis_host: str = os.getenv("REDIS_HOST", "localhost")
        self.redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
        # Le conversazioni scadono da sole (TTL): privacy + niente accumulo.
        self.conversation_ttl_seconds: int = int(os.getenv("CONVERSATION_TTL_SECONDS", "3600"))

        # --- Sicurezza widget / API ---
        # Segreto per firmare i token di sessione. In produzione: valore forte e
        # segreto via env, MAI il default.
        self.session_secret: str = os.getenv("SESSION_SECRET", "dev-session-secret-change-me")
        self.session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "300"))
        # Rate limiting: richieste max per finestra, per chiave (api_key/IP).
        self.rate_limit: int = int(os.getenv("RATE_LIMIT", "60"))
        self.rate_window_seconds: int = int(os.getenv("RATE_WINDOW_SECONDS", "60"))
        # CORS: origini permesse al browser. Default "*" perché la sicurezza vera
        # è server-side (allowlist domini + rate limit + token). In produzione si
        # può restringere. Formato env: lista separata da virgole.
        self.cors_allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")

    @property
    def dsn(self) -> str:
        """Connection string per psycopg."""
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
            f"user={self.db_user} password={self.db_password}"
        )


settings = Settings()
