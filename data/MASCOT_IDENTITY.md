# Mascot Identity Boundary — Quill of Calliope

## Mascot persona: Calliope

**Calliope** è il mascot UI dell'assistente (Live2D sidebar).

- Ruolo: elemento visivo UI, assistant persona
- Tipo: NON è un personaggio di narrativa
- Azioni: reagisce allo stato della scena (emotion sync via WS :9876), espressioni neutre → determinate → gioiose, ecc.
- File: `data/calliope_emotion_map.yaml`, `shared/live2d_mascot/models/calliope/calliope.model3.json`, `app/calliope_shell/static/js/mascot.js`

## RP Character: Aurora

**Aurora** è un personaggio del gioco di ruolo (in-game character, lore-canonico).

- Ruolo: personaggio RP nel setting Yokai/fantasy
- Tipo: personaggio narrativo con scheda (`characters/Aurora.yaml`, ST `external/sillytavern/...Aurora.json`)
- NON coincide con il mascot UI — sono entità separate

## Boundary semantico

| Aspetto | Mascot (Calliope) | RP Character (Aurora) |
|---------|-------------------|----------------------|
| Posizione | Sidebar Flask shell | Scene generate/SillyTavern |
| Controllo | `generate_scene.py` emotion hook | Script narrativo / ST |
| Identità | UI assistant | Personaggio fictizio |
| File | `calliope_emotion_map.yaml` | `characters/Aurora.yaml` |

## Motivazione (G06 P1)

M4_KICKOFF ha esplicitamente raccomandato di evitare "Aurora canon contamination".
Sprint G06 2026-05-19 ha applicato il rename mascot Aurora → Calliope per eliminare
il rischio di drift canon: il mascot non è Aurora, è Calliope.
