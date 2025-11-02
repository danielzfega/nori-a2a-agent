import httpx, os
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")

async def fetch_top_news():
    url = f"https://newsapi.org/v2/top-headlines?country=us&pageSize=5&apiKey={NEWS_API_KEY}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        data = r.json()
        return [a["title"] for a in data.get("articles", []) if a.get("title")]

async def summarize(text: str):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api-inference.huggingface.co/models/facebook/bart-large-cnn",
            headers={"Authorization": f"Bearer {HF_API_KEY}"},
            json={"inputs": text[:2048]}
        )
        js = r.json()
        try:
            return js[0]["summary_text"]
        except:
            return text[:200]
