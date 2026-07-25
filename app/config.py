from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "dev-secret-change-me-please-0123456789"
    database_url: str = "sqlite:///./dispohub.db"
    seed_on_startup: bool = True
    # Produktionsbetrieb hinter HTTPS: Session-Cookie nur über HTTPS senden.
    # Lokal/HTTP auf false lassen, sonst funktioniert der Login nicht.
    session_cookie_secure: bool = False
    # Nur für die automatisierten Tests deaktiviert (die senden Formulare ohne
    # vorher die Seite zu laden) — im echten Betrieb immer True.
    csrf_protection_enabled: bool = True

    app_name: str = "DispoHub"

    @property
    def secret_key_ist_unsicher(self) -> bool:
        return self.secret_key == "dev-secret-change-me-please-0123456789"


settings = Settings()
