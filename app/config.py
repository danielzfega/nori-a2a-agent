from pydantic import BaseSettings, AnyUrl

class Settings(BaseSettings):
    telex_api_key: str
    telex_base_url: str = "https://api.telex.im"
    news_api_key: str
    news_provider: str = "newsapi"  # "newsapi" or "gnews"
    hf_api_key: str | None = None
    hf_model: str = "sshleifer/distilbart-cnn-12-6"
    agent_id: str = "nori-news-agent"
    agent_public_url: AnyUrl
    port: int = 5001
    summarizer_backend: str = "hf_inference"  # or "fallback"

    class Config:
        env_file = ".env"

settings = Settings()
