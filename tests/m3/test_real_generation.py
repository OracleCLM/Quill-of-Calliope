"""Real-gateway smoke tests — skipped if gateway not running."""
import os
import urllib.request
import json
import pytest

GATEWAY = os.environ.get("CALLIOPE_LLM_GATEWAY", "http://localhost:8766")


def _gateway_up() -> bool:
    try:
        urllib.request.urlopen(f"{GATEWAY}/health", timeout=3)
        return True
    except Exception:
        return False


SKIP = pytest.mark.skipif(not _gateway_up(), reason="LLM gateway not running at localhost:8766")


@SKIP
def test_groq_real_call():
    payload = json.dumps({"provider": "groq", "prompt": "Respond with exactly: GROQ_OK"}).encode()
    req = urllib.request.Request(f"{GATEWAY}/llm_ask", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
    assert d["content"], "Empty content from groq"
    assert d["provider"] == "groq"


@SKIP
def test_cerebras_real_call():
    payload = json.dumps({"provider": "cerebras", "prompt": "Respond with exactly: CEREBRAS_OK"}).encode()
    req = urllib.request.Request(f"{GATEWAY}/llm_code", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
    assert d["content"], "Empty content from cerebras"
