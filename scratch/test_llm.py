import os
import asyncio
from app.api.dependencies import get_state
from app.models.query import LLMRequest

os.environ["PYTHONIOENCODING"] = "utf-8"

async def test_llm():
    state = get_state()
    req = LLMRequest(
        query="What is Priya's SSN?",
        context="Priya's SSN is 123.",
    )
    try:
        resp = await state.llm_gateway.query(req)
        print("LLM Success:", resp.raw_text)
    except Exception as e:
        print("LLM Failed:", e)

asyncio.run(test_llm())
