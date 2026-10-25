from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MediaWiki
    mediawiki_api_url: str = "https://prospecting.miraheze.org/w/api.php"

    # Database
    database_url: str = ""

    # Reddit
    reddit_user_agent: str = "PICK/1.0 (Prospecting Information & Community Kit)"
    reddit_subreddit: str = "Prospecting"

    # Webhooks
    webhook_secret: str | None = None

    # App
    app_name: str = "PICK"
    app_version: str = "0.1.0"
    debug: bool = False


settings = Settings()
