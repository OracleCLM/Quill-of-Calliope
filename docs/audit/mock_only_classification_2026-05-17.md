# Mock-Only Audit — Calliope.AI
**Date**: 2026-05-17 (sprint R-CALLIOPE-MOCK-ONLY-AUDIT)
**Pattern**: AP1 Mock Loop Fallacy — mock test PASS ≠ real function works
**Scope**: `tests/` directory, 12 files with mock/patch usage

## Fix Status (sprint R-CALLIOPE-AUDIT-FIX-FALSE-POSITIVES-TOP1, 2026-05-18)

| Finding | Status | Sprint | Notes |
|---------|--------|--------|-------|
| #1 `test_generate_scene_e2e.py` | ✅ **FIXED** 2026-05-18 | TOP1 | Added 4 `@integration` real tests (health/cerebras/groq/e2e), kept unit mock. All 5 PASS. |
| #2 `test_classify_messages.py` | 🟡 **PARTIAL-FIXED** 2026-05-18 | TOP1 | Fixture `tests/fixtures/cerebras_classify_sample.json` captured. 8 format-validation tests PASS. Real API call path still mocked in discord tests. |
| #3 `test_narrative_continuity.py` | ⏳ Deferred | Phase-3 | MED risk — remove mock, test update_from_scene directly |

---

## Summary Stats

| Category | Count | Files |
|----------|-------|-------|
| LEGITIMATE-EXTERNAL | 3 | test_extract_member_list, test_discord_bot, test_twitch_bot |
| LEGITIMATE-INTERNAL | 4 | test_build_chromadb_index, test_merge_char_sources, test_dispatch_to_tier, test_scene_library_expansion |
| POTENTIAL-FALSE-POSITIVE | 3 | test_merge_delta_messages, test_narrative_continuity, test_scene_narrative |
| MISSING-REAL-TEST | 2 | test_classify_messages, test_generate_scene_e2e |

**Total mock-using files**: 12 / total test files: ~30

---

## Per-File Classification

| File | Category | Rationale | Action |
|------|----------|-----------|--------|
| `tests/discord/test_build_chromadb_index.py` | LEGITIMATE-INTERNAL | Mocks ChromaDB+Ollama embedder (heavy infra). Has real idempotency tests. | OK as-is |
| `tests/discord/test_classify_messages.py` | MISSING-REAL-TEST | Mocks cloud LLM API (requests.post). No real call path tested. Rule-based fallback tested. | Add 1 real smoke test (skip if no key) |
| `tests/discord/test_extract_member_list.py` | LEGITIMATE-EXTERNAL | Mocks Discord HTTP API (returns 405 in real). External SDK, correct substitute. | OK as-is |
| `tests/discord/test_merge_char_sources.py` | LEGITIMATE-INTERNAL | Mocks external LLM merge fn. Pure fuzzy+file logic tested directly (18 tests). | OK as-is |
| `tests/discord/test_merge_delta_messages.py` | POTENTIAL-FALSE-POSITIVE | Only mocks sys.argv (argparse). Real merge logic on real JSONL. Low risk. | Consider argparse via argv param instead |
| `tests/m3/test_dispatch_to_tier.py` | LEGITIMATE-INTERNAL | Mocks cloud LLM HTTP gateway. Paired real test in test_real_generation.py (skip if down). | OK as-is |
| `tests/m3/test_generate_scene_e2e.py` | MISSING-REAL-TEST | Mocks dispatch_to_tier entirely. Scene file write tested but LLM path never exercised. | **HIGH risk** — add real smoke (see Task C) |
| `tests/m3/test_narrative_continuity.py` | POTENTIAL-FALSE-POSITIVE | Mocks NarrativeState.update_from_scene (pure Python dataclass, no ext deps). | **MED risk** — remove mock, test directly |
| `tests/m3/test_scene_library_expansion.py` | LEGITIMATE-INTERNAL | Mocks dispatch_to_tier for routing tests. Pure routing logic tested. Real skip tests present. | OK as-is |
| `tests/m3/test_scene_narrative.py` | POTENTIAL-FALSE-POSITIVE | Mocks dispatch_to_tier; chain-building prompt assembly is pure Python. | MED risk — chain logic testable without LLM |
| `tests/m4/test_discord_bot.py` | LEGITIMATE-EXTERNAL | Mocks Discord.py SDK (external, can't run without bot token). Real NarrativeState tests. | OK as-is |
| `tests/m4/test_twitch_bot.py` | LEGITIMATE-EXTERNAL | Mocks httpx + twitchio (external Twitch SDK). Legitimate isolation. | OK as-is |

---

## Task C — Top False Positives (Risk-Ordered)

### 1. `test_generate_scene_e2e.py` — **HIGH**

**Mocked**: `dispatch_to_tier` (entire LLM generation pipeline)
**False Positive Vector**: Mock returns valid scene dict, but real LLM output could be malformed, missing fields, or off-format — breaking downstream scene file writing silently. Only 1 test covers the E2E path.
**Suggested Refactor**: Add `@pytest.mark.skipif(not gateway_up(), reason="gateway down")` real smoke test — call `dispatch_to_tier("groq_fast", "Hello")` and assert non-empty string. Does not require complex setup; gateway already running in CI.
**Risk score**: HIGH — core product feature (scene generation) has no real coverage path.

---

### 2. `test_classify_messages.py` — **HIGH**

**Mocked**: `requests.post` to Groq/Cerebras cloud APIs
**False Positive Vector**: Mock returns clean `{"content": "[\"IC\",\"OOC\"]"}` JSON — but real API returns varied formats (trailing whitespace, `<think>` tags in reasoning models, non-JSON). The JSON-vs-line fallback parser is tested with synthetic inputs that may not match production edge cases.
**Suggested Refactor**: Add `@pytest.mark.skipif` real API smoke test calling `classify_batch(["Hello"])` with real gateway (threshold 1 message). Also add fixture with raw Cerebras response format captured from real call.
**Risk score**: HIGH — classification correctness is data quality gatekeeper for M3+ pipeline.

---

### 3. `test_narrative_continuity.py` — **MED**

**Mocked**: `NarrativeState.update_from_scene` (pure Python dataclass, zero external deps)
**False Positive Vector**: Mock assumes correct update semantics (which chars updated, which plot threads appended, emotion state changes) — but real `update_from_scene` could have bugs in merging logic. 13 tests pass while actual state update behavior is never validated.
**Suggested Refactor**: Remove mock entirely — instantiate real `NarrativeState`, call `update_from_scene(scene_dict)`, assert `state.chars["Aurora"].emotion == "determined"` etc. No external deps needed.
**Risk score**: MED — narrative continuity is RP quality feature, not data pipeline.

---

## AP1 Pattern Reference

> **AP1 Mock Loop Fallacy**: A test suite where all critical paths are mocked creates a false sense of coverage. The tests pass in CI while the real system fails on first live invocation. Key signal: mock ratio > 80% on a file covering core product logic.

Files with zero real execution path for core logic: `test_generate_scene_e2e.py`, `test_narrative_continuity.py`.
Files with partial coverage gap: `test_classify_messages.py` (fallback tested, real format not).

---

## Recommendations

1. **Immediate** (HIGH risk): Add skip-if-gateway-down real smoke to `test_generate_scene_e2e.py`
2. **Next sprint**: Refactor `test_narrative_continuity.py` — remove mock, test `update_from_scene` direct
3. **Deferred**: `test_classify_messages.py` real API fixture capture
4. **OK as-is**: All LEGITIMATE-EXTERNAL + LEGITIMATE-INTERNAL (9/12 files)
