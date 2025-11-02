import httpx
from app.config import settings
from loguru import logger
from app.models import SummaryResult
import asyncio

HF_INFERENCE_URL = "https://api-inference.huggingface.co/models/"

async def summarize_with_hf(text: str, model: str | None = None) -> SummaryResult:
    model = model or settings.hf_model
    url = HF_INFERENCE_URL + model
    headers = {}
    if settings.hf_api_key:
        headers["Authorization"] = f"Bearer {settings.hf_api_key}"
    payload = {"inputs": text, "parameters": {"max_new_tokens": 180, "do_sample": False}}
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        out = r.json()
    # Normalize outputs:
    if isinstance(out, list) and out and isinstance(out[0], dict) and "generated_text" in out[0]:
        summary = out[0]["generated_text"]
    elif isinstance(out, dict) and "summary_text" in out:
        summary = out.get("summary_text")
    elif isinstance(out, str):
        summary = out
    else:
        summary = str(out)[:600]
    return SummaryResult(summary=summary)

async def summarize(text: str) -> SummaryResult:
    backend = settings.summarizer_backend.lower()
    if backend == "hf_inference":
        try:
            return await summarize_with_hf(text, settings.hf_model)
        except Exception as e:
            logger.warning("HF summarizer failed: %s — falling back", e)
            # fall through to fallback
    # Simple fallback: extract first 2 sentences
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    summary = " ".join(sentences[:2]) if sentences else text[:400]
    return SummaryResult(summary=summary)
