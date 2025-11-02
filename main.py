from fastapi import FastAPI, Request
from app.models.a2a import *
from app.services.news import fetch_top_news, summarize
from pydantic import BaseModel
import json

app = FastAPI(title="Nori News Agent", version="1.0.0")


def extract_text_from_parts(parts):
    """
    Extract first text value from mixed Telex message parts:
    handles:
    - { kind: "text", text: "..." }
    - { kind: "data", data: [{ kind: "text", text: "..." }] }
    """
    try:
        for p in parts:
            if p.get("kind") == "text" and p.get("text"):
                return p["text"]

            if p.get("kind") == "data" and isinstance(p.get("data"), list):
                for inner in p["data"]:
                    if inner.get("kind") == "text" and inner.get("text"):
                        return inner["text"]
    except:
        pass
    return None


def safe_parse_rpc(body):
    """
    Try parsing Telex RPC format.
    Fallback gracefully if missing fields.
    """
    try:
        return JSONRPCRequest(**body)
    except Exception:
        class DummyRPC(BaseModel):
            id: str
            method: str
            params: dict
        return DummyRPC(**body)


def extract_prompt(rpc, body):
    # Try modern Telex format w/ messages array
    msg = (
        body.get("params", {}).get("message", {}).get("parts") or
        body.get("params", {}).get("messages", [{}])[-1].get("parts") or
        []
    )

    text = extract_text_from_parts(msg)
    if text:
        # Telex sends taskId here if exists
        task_id = (
            body.get("params", {}).get("message", {}).get("taskId")
            or body.get("params", {}).get("taskId")
            or rpc.id
        )
        return text, task_id

    return "Give me the latest tech news.", rpc.id


@app.post("/a2a/nori")
async def handle_a2a(req: Request):
    body = await req.json()

    print("\n📩 RAW REQUEST:\n", json.dumps(body, indent=2))

    rpc = safe_parse_rpc(body)
    user_prompt, task_id = extract_prompt(rpc, body)

    print("🧠 User Prompt:", user_prompt)

    try:
        headlines = await fetch_top_news()
        raw_news = "\n".join(headlines)
        summary = await summarize(raw_news)

        response_text = f"📰 **Today's Tech Update**\n\n{summary}"
        state = "completed"

    except Exception as e:
        response_text = f"⚠️ Nori error: {str(e)}"
        raw_news = ""
        state = "failed"

    agent_msg = A2AMessage(
        role="agent",
        parts=[MessagePart(kind="text", text=response_text)],
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
    return {"status": "ok", "agent": "Nori"}
