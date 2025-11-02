from fastapi import FastAPI, Request
from app.models.a2a import *
from app.services.news import fetch_top_news, summarize
from pydantic import BaseModel
import json, re

app = FastAPI(title="Nori News Agent", version="1.3.0")


def clean_prompt(text: str) -> str:
    text = re.sub(r"<[^>]*>", "", text)   
    return text.replace("\n", " ").strip()

def extract_text_from_parts(parts):
    # Only look for the last true TEXT message from the USER
    for p in reversed(parts):
        if p.get("kind") == "text" and p.get("text"):
            txt = p["text"].strip()

            # Ignore AI echoes or UI strings
            if txt.lower().startswith(("fetching", "here are", "checking")):
                continue
            if txt.lower() in ["", "<br />", "<p></p>"]:
                continue

            # Strip HTML
            txt = re.sub(r"<[^>]*>", "", txt).strip()

            # Return clean last user text only
            return clean_prompt(txt)

    return None





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
    msg = (
        body.get("params", {}).get("message", {}).get("parts")
        or body.get("params", {}).get("messages", [{}])[-1].get("parts")
        or []
    )

    text = extract_text_from_parts(msg)

    # Default if unclear input
    if not text or len(text) < 2:
        text = "latest news"

    # de-duplicate multiple repeated phrases
    text = re.sub(r"(\b.+?\b)(?:\s+\1\b)+", r"\1", text)

    task_id = (
        body.get("params", {}).get("message", {}).get("taskId")
        or body.get("params", {}).get("taskId")
        or rpc.id
    )

    return text, task_id


# def extract_prompt(rpc, body):
#     msg = (
#         body.get("params", {}).get("message", {}).get("parts")
#         or body.get("params", {}).get("messages", [{}])[-1].get("parts")
#         or []
#     )

#     text = extract_text_from_parts(msg)
#     if text:
#         task_id = (
#             body.get("params", {}).get("message", {}).get("taskId")
#             or body.get("params", {}).get("taskId")
#             or rpc.id
#         )
#         return text, task_id

#     return "Give me the latest tech news.", rpc.id


@app.post("/a2a/nori")
async def handle_a2a(req: Request):
    body = await req.json()
    print("\n📩 RAW REQUEST:\n", json.dumps(body, indent=2))

    rpc = safe_parse_rpc(body)
    user_prompt, task_id = extract_prompt(rpc, body)
    print("🧠 Clean User Prompt:", user_prompt)

    try:
        articles = await fetch_top_news(user_prompt)

        if not articles:
            response_text = (
                f"⚠️ I couldn't find recent results for **{user_prompt}**.\n"
                "Try topics like: `tech`, `breaking news`, `AI`, `startup news`, `crypto`"
            )
            raw_news = ""
            state = "completed"
        else:
            formatted = f"📰 **Top News: {user_prompt}**\n\n"
            raw_news = ""

            for art in articles:
                raw_news += f"{art['title']} - {art['desc']} | {art['url']}\n"
                summary = await summarize(f"{art['title']}. {art['desc'] or ''}")

                formatted += (
                    f"**{art['title']}**\n"
                    f"🔗 {art['url']}\n"
                    f"🏷 Source: {art.get('source', 'Unknown')}\n"
                    f"• {summary}\n\n"
                )

            response_text = formatted
            state = "completed"

    except Exception as e:
        print(f"❌ ERROR: {repr(e)}")  # <-- Add this
        response_text = f"⚠️ Nori Error: {str(e)}"
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
    return {"status": "ok", "agent": "Nori", "version": "1.3.0"}








