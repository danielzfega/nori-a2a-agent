from fastapi import FastAPI, Request
from app.models.a2a import *
from app.services.news import fetch_top_news, summarize

app = FastAPI(title="Nori News Agent", version="1.0.0")

@app.post("/a2a/nori")
async def handle_a2a(req: Request):
    body = await req.json()
    rpc = JSONRPCRequest(**body)

    # Extract user prompt
    if rpc.method == "message/send":
        prompt = rpc.params.message.parts[0].text
        task_id = rpc.params.message.taskId
    else:
        prompt = rpc.params.messages[-1].parts[0].text
        task_id = rpc.params.taskId

    headlines = await fetch_top_news()
    raw = "\n".join(headlines)
    summary = await summarize(raw)

    agent_msg = A2AMessage(
        role="agent",
        parts=[MessagePart(kind="text", text=summary)],
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
