from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TG_TOKEN: str
    PROXY_URL: str | None = None
    BROWSER_PATH: str
    DRIVER_PATH: str
    BROWSER_HEADLESS: bool = True
    PROXY_STATE: bool = False

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')


settings = Settings()
