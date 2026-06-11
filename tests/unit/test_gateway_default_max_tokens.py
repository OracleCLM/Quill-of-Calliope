"""Contract test (gap-review POST-apribile): default max_tokens del gateway HTTP.

Finding: scripts/llm_gateway_http.py ha default max_tokens=1024. zai-glm-4.7 (cerebras,
reasoning-model, post gateway-swap) consuma il budget in reasoning su prompt lunghi →
response senza 'content' → 'ERROR: content'. /draft è stato fixato per-route (4096), MA
generate_variants/dispatch_to_tier e ogni altro consumer cerebras che NON passa max_tokens
eredita il default 1024 → ESPOSTO. Fix sistematico: alzare il default del wrapper.

Source-guard hermetico (come il wiring-guard di VG-1b): groq non è impattato (è solo un cap).
"""
import re
from pathlib import Path


def test_gateway_http_default_max_tokens_reasoning_safe():
    src = (
        Path(__file__).parents[2] / "scripts" / "llm_gateway_http.py"
    ).read_text(encoding="utf-8")
    m = re.search(r"max_tokens:\s*int\s*=\s*(\d+)", src)
    assert m, "campo max_tokens default non trovato in LLMRequest"
    default = int(m.group(1))
    assert default >= 4096, (
        f"default max_tokens={default} troppo basso per i reasoning-model cerebras "
        "(zai-glm-4.7): serve >=4096 o le route cerebras danno 'ERROR: content'"
    )
