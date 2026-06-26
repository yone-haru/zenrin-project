from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Azure OpenAI (GPT-4o Vision / Embeddings)
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_vision_deployment: str = ""
    azure_openai_embedding_deployment: str = ""

    # Azure AI Search
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index_name: str = ""

    # CORS
    cors_allow_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
