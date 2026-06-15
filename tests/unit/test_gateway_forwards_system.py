"""Contract test (gap-review POST-apribile): il gateway wrapper inoltra il `system` prompt.

Finding: scripts/llm_gateway_http.py droppa il campo `system`. Le route (es. /api/translate)
passano system="Output ONLY the translation, no explanations", ma LLMRequest non ha il campo
e _dispatch non lo inoltra a _gw._call_llm (che invece lo SUPPORTA, Workspace server.py:129).
Effetto: il modello ignora l'istruzione → output con preambolo ("The translation to English is:").

Fix: aggiungere system a LLMRequest + inoltrarlo nel _dispatch. Source-guard hermetico.
"""
import re
from pathlib import Path


def _src():
    return (Path(__file__).parents[2] / "scripts" / "llm_gateway_http.py").read_text(encoding="utf-8")


def test_llmrequest_has_system_field():
    src = _src()
    assert re.search(r"system:\s*str\s*\|\s*None\s*=\s*None", src), \
        "LLMRequest deve avere il campo 'system: str | None = None'"


def test_dispatch_forwards_system_to_call_llm():
    src = _src()
    assert re.search(r"system\s*=\s*req\.system", src), \
        "_dispatch deve inoltrare system=req.system a _gw._call_llm"
