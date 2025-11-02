import httpx
from app.config import settings
from loguru import logger
from typing import List
from app.models import NewsArticle

NEWSAPI_BASE = "https://newsapi.org/v2"

async def top_headlines(query: str | None = None, country: str | None = None, category: str | None = None, page_size: int = 5) -> List[NewsArticle]:
    params = {"apiKey": settings.news_api_key, "pageSize": page_size}
    if query:
        params["q"] = query
    if country:
        params["country"] = country
    if category:
        params["category"] = category
    url = f"{NEWSAPI_BASE}/top-headlines"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    articles = []
    for a in data.get("articles", []):
        articles.append(NewsArticle(
            title=a.get("title") or "",
            url=a.get("url") or "",
            source=(a.get("source") or {}).get("name"),
            description=a.get("description") or ""
        ))
    logger.debug("Fetched %d articles", len(articles))
    return articles
