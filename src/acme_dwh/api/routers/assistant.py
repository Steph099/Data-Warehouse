"""/assistant endpoint — grounded LLM assistant over the MCP tools."""
from __future__ import annotations

from fastapi import APIRouter

from acme_dwh.api.schemas import AssistantRequest, AssistantResponse
from acme_dwh.mcp.agent import run_agent

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/ask", response_model=AssistantResponse, summary="Ask the assistant (tool-calling, grounded)")
def ask(body: AssistantRequest) -> AssistantResponse:
    # sync handler -> FastAPI threadpool; run_agent drives Ollama + the MCP tools
    return AssistantResponse(**run_agent(body.question))
