# Quill of Calliope

> Musa della poesia epica. Assistente AI per narrazione e gestione di giochi di ruolo testuali.

**Status**: M0 SCAFFOLD (2026-05-16). In active brainstorming/setup. NOT production-ready.

## Cosa è

Quill of Calliope aiuta a:
- **Generare drafts** di risposte RP in inglese literate partendo da intent italiano
- **Tracciare context** persistente cross-sessione (char sheets + lore + scene attive)
- **Tradurre** italiano → inglese con vocabolario fantasy coerente
- **Importare** storico Excel/ChatGPT/Discord in knowledge base ChromaDB
- **Sostenere temi sensibili** (violenza/dark/erotica narrativamente giustificati) via LLM locali abliterated

Privacy-first, local-only, MCP-driven per token saving.

## Quick start

⚠️ MVP in costruzione. Quick start sarà disponibile post-M2 (skill core).

Pre-requisiti pianificati:
- Linux (NM development) + WSL2 se servirà cross-platform
- Python 3.13 (anaconda3)
- Ollama (modelli locali)
- Claude API key (uso minimal, scene critical)
- Cerebras + Groq MCP gateway (via Claude-OPs `.mcp.json`)
- libreoffice CLI (per Excel .xls → .xlsx conversion)

## Vision

Vedi [VISION.md](VISION.md) per scope completo, roadmap M0-M6, LLM strategy 4-tier, privacy policy, anti-pattern.

## Status milestone

- 🟢 M0 SCAFFOLD (2026-05-16) — repo struttura + VISION + .gitignore + manifest
- ⬜ M1 IMPORT — Excel + ChatGPT + Discord parsers + ChromaDB index
- ⬜ M2 SKILLS CORE — 5 skill custom calliope-*
- ⬜ M3 CLI — TUI Textual + commands base
- ⬜ M4 SILLYTAVERN EVAL — integration + Path C decision consolidation
- ⬜ M5 PRODUCTION — daily-usable
- ⬜ M6 — Discord bot semi-auto + TTS

## Refs

Repo gemelli pattern: [Atlante](../Atlante) (enterprise deploy curated subset) + [Claude-OPs](../Claude-OPs) (orchestration toolkit).

## License

TBD. Probabile MIT (coerente Claude-OPs/Atlante). Verificare se AGPL-3.0 si applica per coerenza upstream OBLITERATUS.
