from fastapi import FastAPI, Request
from app.models.a2a import *
from app.services.news import fetch_top_news, summarize
from pydantic import BaseModel
import json, re

app = FastAPI(title="Nori News Agent", version="2.0.0")

# --- Helper Utilities ---

def clean_prompt(text: str) -> str:
    text = re.sub(r"<[^>]*>", "", text)
    return text.replace("\n", " ").strip()

def extract_text_from_parts(parts):
    """Extract *real* user query, not system echo or UI text."""
    
    candidates = []

    for p in parts:
        if p.get("kind") == "text" and p.get("text"):
            txt = p["text"].strip()

            # remove HTML garbage
            txt = re.sub(r"<[^>]*>", "", txt).strip()

            # block UI/system chatter
            blocked_prefixes = [
                "fetching", "checking", "here are",
                "fetch", "checking", "loading",
                "give me", "getting"
            ]
            if any(txt.lower().startswith(b) for b in blocked_prefixes):
                continue

            # ignore empty or filler
            if txt in ["", "<br />", "<p></p>"]:
                continue

            # ignore links
            if re.match(r"^https?://", txt.lower()):
                continue

            # Only keep meaningful user text
            if len(txt) > 2:
                candidates.append(txt)

    return clean_prompt(candidates[-1]) if candidates else None

def safe_parse_rpc(body):
    try:
        return JSONRPCRequest(**body)
    except Exception:
        class DummyRPC(BaseModel):
            id: str
            method: str
            params: dict
        return DummyRPC(**body)

def extract_prompt(rpc, body):
    parts = (
        body.get("params", {}).get("message", {}).get("parts")
        or body.get("params", {}).get("messages", [{}])[-1].get("parts")
        or []
    )

    text = extract_text_from_parts(parts)

    # Default fallback — do *not* restrict to tech
    if not text:
        text = "latest world news"

    # remove repeated phrase glitches
    text = re.sub(r"(\b.+?\b)(?:\s+\1\b)+", r"\1", text)

    task_id = (
        body.get("params", {}).get("message", {}).get("taskId")
        or body.get("params", {}).get("taskId")
        or rpc.id
    )

    return text, task_id

# --- Main A2A Handler ---

@app.post("/a2a/nori")
async def handle_a2a(req: Request):
    body = await req.json()
    print("\n📩 RAW REQUEST:\n", json.dumps(body, indent=2))

    rpc = safe_parse_rpc(body)
    user_prompt, task_id = extract_prompt(rpc, body)
    print("🧠 User Asked:", user_prompt)

    try:
        articles = await fetch_top_news(user_prompt)

        if not articles:
            response = (
                f"⚠️ Couldn't find recent results for **{user_prompt}**.\n"
                "Try topics like: tech, AI, crypto, China, Africa, startups, geopolitics."
            )
            raw_news = ""
            state = "completed"
        else:
            formatted = f"📰 **Top News: {user_prompt}**\n\n"
            raw_news = ""

            for art in articles:
                raw_news += f"{art['title']} - {art['desc']} | {art['url']}\n"

                # better summary prompt
                summary = await summarize(
                    f"Give 2-3 short bullet points summarizing this news:\n{art['title']} - {art['desc']}"
                )

                summary = summary.replace("-", "•").strip()

                formatted += (
                    f"**{art['title']}**\n"
                    f"🔗 {art['url']}\n"
                    f"🏷 Source: {art.get('source', 'Unknown')}\n"
                    f"{summary}\n\n"
                )

            response = formatted
            state = "completed"

    except Exception as e:
        print("❌ ERROR:", repr(e))
        response = f"⚠️ Nori Error: {str(e)}"
        raw_news = ""
        state = "failed"

    agent_msg = A2AMessage(
        role="agent",
        parts=[MessagePart(kind="text", text=response)],
        taskId=task_id
    )

    result = TaskResult(
        id=task_id,
        contextId="nori-context",
        status=TaskStatus(state=state, message=agent_msg),
        artifacts=[Artifact(name="news_raw", parts=[MessagePart(kind="text", text=raw_news)])],
        history=[agent_msg]
    )

    return JSONRPCResponse(id=rpc.id, result=result).model_dump()


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Nori", "version": "2.0.0"}
