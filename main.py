import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from app.config import settings
from app.models import JSONRPCRequest, JSONRPCResponse, TelexMessageEvent, NewsArticle
from app.a2a import handle_jsonrpc
from app.telex_client import TelexClient
from app.news_client import top_headlines
from app.summarizer import summarize
from app.nlu import parse_user_query
from loguru import logger
import json

app = FastAPI(title="Nori - A2A News Agent")
telex = TelexClient()

@app.get("/.well-known/agent.json")
async def agent_card():
    return {
        "id": settings.agent_id,
        "name": "Nori",
        "description": "Nori — friendly news summarizer for Telex.im",
        "url": str(settings.agent_public_url),
        "capabilities": ["news.search", "news.fetch", "notifications"],
        "endpoints": {
            "a2a": f"{settings.agent_public_url}/a2a/jsonrpc",
            "events": f"{settings.agent_public_url}/webhook/events"
        }
    }

@app.post("/a2a/jsonrpc")
async def a2a_jsonrpc(req: Request):
    body = await req.json()
    rpc = JSONRPCRequest(**body)
    # quick dispatch for simple methods; main handle_jsonrpc has agent.info
    if rpc.method in ("news.search", "news.fetch"):
        try:
            if rpc.method == "news.search":
                params = rpc.params or {}
                query = params.get("query")
                country = params.get("country")
                category = params.get("category")
                # call news client
                articles = await top_headlines(query=query, country=country, category=category, page_size=5)
                # summarize each article quickly (in parallel)
                tasks = [summarize((a.description or a.title)[:2000]) for a in articles]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                out = []
                for art, res in zip(articles, results):
                    if isinstance(res, Exception):
                        summary_text = (art.description or art.title)[:300]
                    else:
                        summary_text = res.summary
                    out.append({"title": art.title, "url": art.url, "summary": summary_text, "source": art.source})
                return JSONRPCResponse(id=rpc.id, result={"articles": out}).model_dump()
            elif rpc.method == "news.fetch":
                params = rpc.params or {}
                url = params.get("url")
                # naive: fetch url, take text snippet and summarize
                async with httpx.AsyncClient() as client:
                    r = await client.get(url, timeout=30)
                    r.raise_for_status()
                    text = r.text[:4000]
                summ = await summarize(text)
                return JSONRPCResponse(id=rpc.id, result={"summary": summ.summary}).model_dump()
        except Exception as e:
            logger.exception("Error handling JSON-RPC method")
            return JSONRPCResponse(id=rpc.id, error={"message": str(e)}).model_dump()
    else:
        # delegate to generic handler for agent.info etc
        try:
            resp = await handle_jsonrpc(rpc)
            return resp.model_dump()
        except Exception as e:
            logger.exception("A2A handler error")
            return JSONRPCResponse(id=rpc.id, error={"message": str(e)}).model_dump()

@app.post("/webhook/events")
async def webhook(event: TelexMessageEvent, background: BackgroundTasks):
    """
    Entry for Telex webhook events (message.created etc).
    Detects natural-language news requests and responds via DM.
    """
    # quick guard
    if event.event_type not in ("message.created", "message.posted", "message.new"):
        return {"status": "ignored"}

    # parse user's message for news intent
    topic, country, days = parse_user_query(event.content)
    if not (topic or "news" in event.content.lower()):
        return {"status": "not-news-query"}

    # background process the request
    background.add_task(process_news_request, event, topic, country, days)
    return {"status": "accepted"}

import asyncio, httpx

async def process_news_request(event: TelexMessageEvent, topic: str | None, country: str | None, days: int | None):
    try:
        # Map topic to category for NewsAPI (if topic None, use general/top)
        category = topic if topic in ("business","entertainment","general","health","science","sports","technology","politics") else None
        query = None
        if topic and category is None:
            query = topic

        articles = await top_headlines(query=query, country=country, category=category, page_size=5)
        if not articles:
            await telex.send_dm(event.author_id, "Sorry — I couldn't find recent stories for that query.")
            return

        # Summarize in parallel (limit concurrency)
        tasks = [summarize((a.description or a.title)[:2000]) for a in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        parts = []
        for art, res in zip(articles, results):
            summary_text = res.summary if not isinstance(res, Exception) else (art.description or art.title)
            parts.append(f"📰 {art.title}\n\n{summary_text}\n\nRead: {art.url}\nSource: {art.source}\n")

        message = f"Here are the latest headlines you asked for ({topic or 'top headlines'}):\n\n" + "\n\n".join(parts)
        await telex.send_dm(event.author_id, message)
    except Exception as e:
        logger.exception("Failed to process news request")
        try:
            await telex.send_dm(event.author_id, f"Sorry, Nori encountered an error: {e}")
        except Exception:
            logger.exception("Failed to send fallback DM")

@app.on_event("shutdown")
async def shutdown_event():
    await telex.close()

def run():
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)

if __name__ == "__main__":
    run()
