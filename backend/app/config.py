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

        # --- Modello di embedding locale (dev via Ollama) ---
        self.ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "bge-m3")
        self.embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "1024"))

    @property
    def dsn(self) -> str:
        """Connection string per psycopg."""
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
            f"user={self.db_user} password={self.db_password}"
        )


settings = Settings()
