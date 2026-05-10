from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    google_places_api_key: str | None = None
    google_places_text_search_url: str = "https://places.googleapis.com/v1/places:searchText"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    coverage_min_places: int = 12

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
