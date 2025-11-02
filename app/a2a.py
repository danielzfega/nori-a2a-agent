from app.models import JSONRPCRequest, JSONRPCResponse
from fastapi import HTTPException
from typing import Any
from app.config import settings

async def handle_jsonrpc(req: JSONRPCRequest) -> JSONRPCResponse:
    """
    Dispatch JSON-RPC methods here.
    Supported methods:
      - agent.info -> returns metadata
      - news.search -> params: { query, country?, category?, days? }
      - news.fetch  -> params: { url } (fetch full article + summarize)
    """
    method = req.method
    if method == "agent.info":
        return JSONRPCResponse(id=req.id, result={
            "id": settings.agent_id,
            "name": "Nori",
            "description": "Nori — friendly news summarizer",
            "capabilities": ["news.search", "news.fetch", "notifications"],
            "endpoints": {
                "a2a": f"{settings.agent_public_url}/a2a/jsonrpc",
                "events": f"{settings.agent_public_url}/webhook/events"
            }
        })
    # the rest of handlers are implemented in main.py to reuse clients (or you can import services)
    raise HTTPException(status_code=404, detail=f"Method {method} not found")
