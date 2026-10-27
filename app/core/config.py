from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agent Release Gate"
    app_version: str = "0.3.0"
    environment: str = "development"
    database_url: str = "sqlite:///./agent_release_gate.db"
    admin_api_key: str = "change-me"
    session_secret_key: str = "change-me-session-secret"
    default_page_size: int = 20
    max_page_size: int = 100
    public_form_enabled: bool = True
    request_rate_limit_per_minute: int = 30
    max_prompt_length: int = 10_000
    auto_create_sqlite_schema: bool = True
    # Only trust X-Forwarded-For when a reverse proxy you control sets it.
    # Otherwise any client can rotate the header to dodge rate limits.
    trust_proxy_headers: bool = False
    # Send the session cookie only over HTTPS. Turn on in any deployed environment.
    session_https_only: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
