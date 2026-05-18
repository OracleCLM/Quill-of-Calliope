#!/usr/bin/env python3
"""HTTP bridge for MCP llm-gateway — exposes Groq/Cerebras/OpenRouter via REST."""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# Inject gateway server into path — must precede downstream imports  # noqa: E402
_GW_PATH = Path("/home/nic/Scrivania/Workspace/mcp_servers/llm_gateway")
sys.path.insert(0, str(_GW_PATH))

import server as _gw  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from pydantic import BaseModel  # noqa: E402
import uvicorn  # noqa: E402

app = FastAPI(title="calliope-llm-gateway-http", version="1.0")


class LLMRequest(BaseModel):
    provider: str  # "groq" | "cerebras" | "openrouter"
    prompt: str
    max_tokens: int = 1024
    temperature: float = 0.7


class LLMResponse(BaseModel):
    content: str
    provider: str
    model: str


@app.get("/health")
def health():
    return {"status": "ok", "providers": list(_gw.PROVIDERS.keys())}


@app.post("/llm_ask", response_model=LLMResponse)
async def llm_ask(req: LLMRequest):
    """Fast Q&A — uses groq by default."""
    return await _dispatch(req)


@app.post("/llm_code", response_model=LLMResponse)
async def llm_code(req: LLMRequest):
    """Heavy codegen/reasoning — uses cerebras by default."""
    return await _dispatch(req)


async def _dispatch(req: LLMRequest) -> LLMResponse:
    cfg = _gw.PROVIDERS.get(req.provider)
    if not cfg:
        raise HTTPException(400, f"Unknown provider: {req.provider!r}")
    model = cfg["default_model"]
    try:
        content = await _gw._call_llm(
            req.provider,
            req.prompt,
            model=model,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
        return LLMResponse(content=content, provider=req.provider, model=model)
    except Exception as exc:
        logging.error("LLM call failed: %s", exc)
        raise HTTPException(502, f"LLM call failed: {exc}") from exc


def main():
    parser = argparse.ArgumentParser(
        description="Calliope LLM Gateway HTTP bridge"
    )
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--daemon", action="store_true")
    args = parser.parse_args()

    if args.daemon:
        pid_path = Path("/tmp/calliope_llm_gateway.pid")
        log_path = Path("/tmp/calliope_llm_gateway.log")
        proc = subprocess.Popen(
            [sys.executable, __file__, "--port", str(args.port), "--host", args.host],
            stdout=log_path.open("w"),
            stderr=subprocess.STDOUT,
        )
        pid_path.write_text(str(proc.pid))
        print(f"Daemon started PID={proc.pid}, log={log_path}")
        return

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
