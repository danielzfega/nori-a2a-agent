import httpx, os
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")


async def fetch_top_news(query: str):
    """
    Flexible news search:
    - If user asks general news → still return global/tech by default
    - If user asks specific question → use their query
    """

    if not query or len(query.strip()) < 2:
        query = "technology OR startups OR AI"

    url = "https://newsapi.org/v2/everything"

    params = {
        "q": query,
        "sortBy": "publishedAt",
        "pageSize": 5,
        "language": "en",
        "apiKey": NEWS_API_KEY
    }

    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        data = r.json()

    articles = data.get("articles", [])
    cleaned = []

    for a in articles:
        cleaned.append({
            "title": a.get("title"),
            "url": a.get("url"),
            "source": a.get("source", {}).get("name"),
            "desc": a.get("description")
        })

    return cleaned



async def summarize(text: str):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api-inference.huggingface.co/models/facebook/bart-large-cnn",
            headers={"Authorization": f"Bearer {HF_API_KEY}"},
            json={"inputs": text[:1024]}
        )
        js = r.json()

        try:
            return js[0]["summary_text"]
        except:
            return text[:200]
