from pydantic import BaseModel
from typing import Any, Optional, List, Dict

# JSON-RPC A2A models (minimal)
class JSONRPCRequest(BaseModel):
    jsonrpc: str
    id: Optional[str]
    method: str
    params: Optional[Dict[str, Any]] = {}

class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str]
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

# Telex webhook message (simplified)
class TelexMessageEvent(BaseModel):
    event_type: str
    message_id: str
    channel_id: Optional[str]
    channel_name: Optional[str]
    author_id: str
    author_name: Optional[str]
    content: str
    timestamp: Optional[str]

# News item / summary shapes
class NewsArticle(BaseModel):
    title: str
    url: str
    source: Optional[str] = None
    description: Optional[str] = None

class SummaryResult(BaseModel):
    summary: str
    highlights: Optional[List[str]] = []
