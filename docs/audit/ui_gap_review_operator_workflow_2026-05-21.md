# UI Gap Review — Operator Workflow 5-Step
**Sprint**: R-CALLIOPE-UI-USABILITY-DEEP-REVIEW-WAVE-5
**Date**: 2026-05-21
**Worker**: sonnet1-calliope
**MCP**: mcp__semble__search (route analysis), mcp__playwright__browser_* (UI verify)

---

## Gap Table JSON

```json
{
  "step_1_open_ui": {
    "status": "BROKEN",
    "details": "Main view = iframe src=ST_URL. SillyTavern NOT running on :8001 → main view BLANK. Operator confirmed: 'Last time UI nearly empty'. Root cause: ST dependency not fallback-handled."
  },
  "step_2_retrieve_msg": {
    "status": "MISSING",
    "gap": "No /api/messages/recent route exists. No UI element for message retrieval. ChromaDB calliope_messages has 29308 docs but zero UI surface. Nav has no Messages tab."
  },
  "step_3_select_scene": {
    "status": "MISSING",
    "gap": "332 scenes/*.draft.yaml exist but NO /api/scenes route, NO scene picker UI. The only scene reference is in Arc panel (/api/arc) but scenes there are Arc-attached summaries, not the raw YAML scene files."
  },
  "step_4_request_gen": {
    "status": "MISSING",
    "gap": "/api/scene/variants exists (full scene generation from prompt) but NO context-aware continuation endpoint. No /api/messages/next that takes scene_id + char + last_msg → generates next character message."
  },
  "step_5_output_visible": {
    "status": "PARTIAL",
    "details": "Draft tab shows variants output. Arc tab shows continue result. But both require multi-step navigation and neither surfaces the 5-step workflow linearly. No single flow: messages → scene → generate → output."
  }
}
```

---

## Workflow Trace (per step)

| Step | UI Element | Route | Status |
|------|-----------|-------|--------|
| 1. Open UI | `GET /` → shell.html | `/` | BROKEN (ST blank) |
| 2. Retrieve last N msg | — | — | MISSING |
| 3. Select scene | — | — | MISSING |
| 4. Request generation next-msg | Draft tab (scene_variants only) | `/api/scene/variants` | PARTIAL (wrong type) |
| 5. Output visible | Draft variants output | — | PARTIAL |

## Empty-state diagnosis

- `ST_URL` = `http://localhost:8001` (env default)
- ST NOT running → iframe loads blank page
- **Fix (Gap D)**: Added `st_alive` flag in `GET /` (HEAD check with 1s timeout). Template renders welcome panel with 4 quick-action cards when ST down.

## Nav usability

Current tabs: Home | Translate | ✦ Draft | ✎ Refine | ◈ Arc
- Home = ST iframe (BLANK if ST down)
- No "Messages" tab
- No "Scenes" tab
- **Fix**: Added `◇ Messages` and `◆ Scenes` as first two tabs in nav (most important for operator workflow)

## Retrieve-messages capability

- ChromaDB `calliope_messages`: **29308 docs** (rich corpus)
- **Gap**: ZERO UI surface, ZERO Flask route
- **Fix (Gap A)**: Added `GET /api/messages/recent?limit=N&char=<name>` → ChromaDB query → list view

## Scene-selector capability

- `scenes/*.draft.yaml`: **332 files** with rich metadata (scene_id, title, summary, participants, excerpts)
- **Gap**: No route, no UI
- **Fix (Gap B)**: Added `GET /api/scenes?filter=<text>` + `GET /api/scenes/<scene_id>` + Scenes panel with filter input, scrollable list, detail view

## Generate-next-msg capability

- `/api/scene/variants`: generates new scene from prompt — NOT continuation
- **Gap**: No context-aware continuation endpoint
- **Fix (Gap C)**: Added `POST /api/messages/next` — takes scene_id + char + last_msg → builds context prompt (char_memory recall + scene meta + last_msg) → calls Groq → returns next_msg

---

## Implementation summary (Phase 3 deliverables)

| Gap | Route | UI Element | Status |
|-----|-------|-----------|--------|
| A: Retrieve messages | `GET /api/messages/recent` | `#messages-panel` tab | IMPLEMENTED |
| B: Scene selector | `GET /api/scenes`, `GET /api/scenes/<id>` | `#scenes-panel` tab + filter | IMPLEMENTED |
| C: Generate next-msg | `POST /api/messages/next` | Continue ▶ button in scene detail | IMPLEMENTED |
| D: ST empty-state | `GET /` st_alive check | Welcome panel + 4 cards | IMPLEMENTED |
