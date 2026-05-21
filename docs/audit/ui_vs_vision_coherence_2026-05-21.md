# UI vs VISION Coherence Check
**Sprint**: R-CALLIOPE-UI-USABILITY-DEEP-REVIEW-WAVE-5
**Date**: 2026-05-21
**Source**: CALLIOPE_VISION_REFINEMENT_FROM_GPT_RPG_2026-05-19.md §2 patterns operator

---

## Match Table: Empirical Pattern → UI Surface

| Pattern (freq) | UI Surface pre-sprint | UI Surface post-sprint |
|---|---|---|
| bilingual_translation_IT_EN (HIGH) | ✓ Translate tab | ✓ unchanged |
| world_building_lore_expansion (HIGH) | ⚠ ChromaDB exists, no UI route | ⚠ unchanged (P2 gap — future) |
| story_development_plot_chars (HIGH) | ⚠ Arc tab (partial) | ✓ Scenes tab + Continue ▶ now surfaces char-scoped generation |
| tone_range_serious_to_ribald (HIGH) | ⚠ generate_scene exists, no UI filter | ⚠ unchanged |
| discord_workflow_native (HIGH) | ⚠ Discord bot PARTIAL (no token) | ⚠ unchanged |
| multi_char_memory_recall (MED) | ✓ /api/char/recall exists, sidebar | ✓ char_memory integrated in Continue ▶ context |
| **numbered_variants_then_blend (MED)** | ✓ Draft tab (WAVE3) | ✓ unchanged |
| iterative_refinement_passes (MED) | ✓ Refine tab | ✓ unchanged |
| anti_GPT_cliche_lexicon (LOW-signal) | ✓ style_filter + Refine auto-lint | ✓ unchanged |

---

## VISION Gaps still open (not in scope this sprint)

1. **world_building_lore_expansion**: `/lore search` exists in CLI but NO Flask route or UI surface. ChromaDB `calliope_scenes` (303) + `calliope_characters` (118) accessible but no lore-specific UI.
2. **discord_workflow_native**: Bot implemented (WAVE4) but requires operator-set bot token.
3. **tone_range_serious_to_ribald**: No routing filter for humor/ribald in scene generation UI.

---

## VISION Refinement Proposal

Add `§0 Operator Workflow Primary` hard constraint to VISION.md:

```
## §0 — Operator Workflow Primary (2026-05-21 — empirical-driven)

UI MUST support operator workflow end-to-end without terminal:
1. Retrieve last N messages (◇ Messages tab)
2. Select scene (◆ Scenes tab + filter)
3. Generate next character message (Continue ▶ button)
4. View output inline (no file download required)

All Flask features with non-zero empirical operator usage MUST have
a corresponding clickable UI element. CLI-only features are staging only.
```

---

## Coherence verdict

**Pre-sprint**: LOW coherence — high-freq patterns (story_development, multi_char_memory_recall, discord_native) had backend routes but ZERO UI surfaces for the canonical 5-step workflow.

**Post-sprint**: MEDIUM-HIGH coherence — gaps A/B/C/D implemented, operator can now run full 5-step workflow without terminal. Remaining gaps (lore, tone-filter, discord-token) are P2-P3.
