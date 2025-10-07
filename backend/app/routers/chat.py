from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..schemas import ChatRequest
from ..services.agent import run_agent_stream


router = APIRouter(prefix="/api", tags=["chat"])


def _format_sse(event: str, data: str) -> bytes:
    return f"event: {event}\ndata: {data}\n\n".encode("utf-8")


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    async def event_gen() -> AsyncGenerator[bytes, None]:
        try:
            async for item in run_agent_stream(req.session_id, req.message):
                if item.get("type") == "message":
                    yield _format_sse("message", json.dumps({"content": item.get("content")}))
                elif item.get("type") == "tool_result":
                    yield _format_sse("tool_result", json.dumps({"name": item.get("name"), "result": item.get("result")}))
        except Exception as e:
            yield _format_sse("error", json.dumps({"message": str(e)}))
        finally:
            yield _format_sse("done", json.dumps({}))

    return StreamingResponse(event_gen(), media_type="text/event-stream")


