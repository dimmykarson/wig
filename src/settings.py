from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 5504
    mock_base_url: str = "http://localhost:5504"
    app_secret: str = "mock-secret"
    verify_token: str = "mock-verify-token"
    log_level: str = "INFO"
    max_debug_entries: int = 50
    status_delivered_delay_ms: int = 1000
    status_read_delay_ms: int = 3000
    ws_inactivity_timeout_s: int = 300  # 5 min — server closes idle connections

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
