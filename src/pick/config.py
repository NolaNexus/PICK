from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://pick:pick@localhost:5432/pick"
    test_database_url: str = "postgresql+psycopg2://pick:pick@localhost:5432/pick_test"
    wiki_api_url: str = "https://prospecting.miraheze.org/w/api.php"
    wiki_maxlag: int = 5
    wiki_user_agent: str = "PICK-pipeline/0.1"
    git_public_repo: str = "/home/nola/Desktop/pick-site"
    log_file: str = "/home/nola/Desktop/PICK!/logs/refresh.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
