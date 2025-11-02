from fastapi import FastAPI, Request
from app.models.a2a import *
from app.services.news import fetch_top_news, summarize

app = FastAPI(title="Nori News Agent", version="1.0.0")

@app.post("/a2a/nori")
async def handle_a2a(req: Request):
    body = await req.json()
    rpc = JSONRPCRequest(**body)

    # Extract user prompt safely for both a2a request formats
    user_prompt = ""

    if rpc.method == "message/send":
        # v1 style messaging
        parts = rpc.params.message.parts
        # Extract first text part
        for p in parts:
            if p.kind == "text":
                user_prompt = p.text
                break
        task_id = getattr(rpc.params.message, "taskId", rpc.id)

    else:
        # v2 execution call (assistant / workflow use)
        messages = rpc.params.messages
        last_msg = messages[-1]
        for p in last_msg.parts:
            if p.kind == "text":
                user_prompt = p.text
                break
        task_id = rpc.params.taskId

    # === AGENT LOGIC ===
    headlines = await fetch_top_news()
    raw = "\n".join(headlines)
    summary = await summarize(raw)

    agent_msg = A2AMessage(
        role="agent",
        parts=[MessagePart(kind="text", text=f"📰 **Today's Tech Update**\n\n{summary}")],
        taskId=task_id
    )

    result = TaskResult(
        id=task_id,
        contextId="nori-context",
        status=TaskStatus(state="completed", message=agent_msg),
        artifacts=[Artifact(name="news_raw", parts=[MessagePart(kind="text", text=raw)])],
        history=[agent_msg]
    )

    return JSONRPCResponse(id=rpc.id, result=result).model_dump()

@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Nori"}
