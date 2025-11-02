from fastapi import FastAPI, Request
from app.models.a2a import *
from app.services.news import fetch_top_news, summarize
import json

app = FastAPI(title="Nori News Agent", version="1.0.0")


def extract_prompt(rpc: JSONRPCRequest):
    """
    Extract text safely from Telex message formats (v1 + v2)
    """
    user_prompt = ""

    try:
        # A2A v1 -> method = "message/send"
        if rpc.method == "message/send":
            parts = rpc.params.message.parts
            for p in parts:
                if p.kind == "text" and p.text:
                    return p.text, getattr(rpc.params.message, "taskId", rpc.id)

        # A2A v2 -> method = "execute"
        else:
            last_msg = rpc.params.messages[-1]
            for p in last_msg.parts:
                if p.kind == "text" and p.text:
                    return p.text, rpc.params.taskId

    except Exception:
        pass

    return "Give me the latest tech news.", rpc.id


@app.post("/a2a/nori")
async def handle_a2a(req: Request):
    body = await req.json()

    # Debug print (keep for now)
    print("\n📩 RAW A2A REQUEST:\n", json.dumps(body, indent=2))

    rpc = JSONRPCRequest(**body)
    user_prompt, task_id = extract_prompt(rpc)

    # === Agent Logic ===
    try:
        headlines = await fetch_top_news()
        raw_news = "\n".join(headlines)

        summary = await summarize(raw_news)
        response_text = f"📰 **Today's Tech Update**\n\n{summary}"

        state = "completed"

    except Exception as e:
        response_text = f"⚠️ Nori had an issue processing the news: {str(e)}"
        raw_news = ""
        state = "failed"

    # === Build Response ===
    agent_message = A2AMessage(
        role="agent",
        parts=[MessagePart(kind="text", text=response_text)],
        taskId=task_id
    )

    result = TaskResult(
        id=task_id,
        contextId="nori-context",
        status=TaskStatus(state=state, message=agent_message),
        artifacts=[
            Artifact(name="news_raw", parts=[MessagePart(kind="text", text=raw_news)])
        ],
        history=[agent_message]
    )

    return JSONRPCResponse(id=rpc.id, result=result).model_dump()


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Nori"}
