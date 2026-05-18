# Vesta-Minerva → Quill of Calliope reuse map

> Mapping componenti riutilizzabili da Vesta-Minerva (Workspace sub-system) per Quill of Calliope persona+memory tracking.

## Cosa è Vesta-Minerva

Workspace sub-project per persona tracking + emotional state + persistent memory + multi-channel routing. Locato in `~/Scrivania/Workspace/vesta_system1/`.

Funzioni core esistenti:
- Identity tracking per personaggio/utente cross-session
- Emotional state machine (valenza/arousal/dominance VAD model)
- Memory store persistente (Mem0 wrapper + ChromaDB backend)
- Multi-channel routing (Telegram/voice/iMessage adapter)
- Constitutional gate pre-output

## Componenti riutilizzabili per Quill of Calliope

### ✅ HIGH-VALUE reuse

| Componente Vesta | Path approssimativo | Quill of Calliope use case | Adattamento |
|------------------|---------------------|---------------------|-------------|
| **Persona tracker** | `vesta_system1/persona_tracker.py` | Tracking NPC + PC across scenes | Adapt: char_id invece di user_id |
| **Memory store Mem0 wrapper** | `vesta_system1/memory_store.py` | Persistent memory per char + lore | Riusa diretto, separate namespace `calliope_*` |
| **Emotional state machine** | `vesta_system1/emotional_state.py` | Char mood tracking durante scene | Adapt: char-level invece di session-level |
| **Constitutional gate** | `vesta_system1/constitutional_gate.py` | Pre-output safety check | Bypass per Calliope (uncensored intenzionale per RP) MA keep base structure |

### 🟡 MEDIUM-VALUE reuse

| Componente Vesta | Quill of Calliope use case |
|------------------|---------------------|
| ChromaDB wrapper | Riuso pattern, separate shard |
| Conversational history schema | Adapt per scene history |
| Channel routing | NOT applicable (Calliope no multi-channel) |

### ❌ NOT applicable

- TG bot integration → Calliope no Telegram (per ora)
- Voice/iMessage adapters → Calliope no multi-channel
- Trading-specific gates → not RP related

## Implementazione strategy

### Path A — Import as library

Crea `~/Scrivania/Quill_of_Calliope/src/vesta_lib/` directory locale:
```python
# Setup
mkdir -p ~/Scrivania/Quill_of_Calliope/src/vesta_lib
# Copia files riutilizzabili (NO modify originale Workspace)
cp ~/Scrivania/Workspace/vesta_system1/persona_tracker.py src/vesta_lib/
cp ~/Scrivania/Workspace/vesta_system1/memory_store.py src/vesta_lib/
cp ~/Scrivania/Workspace/vesta_system1/emotional_state.py src/vesta_lib/
```

Adapt:
- Cambia `user_id` → `char_id` in persona_tracker
- Namespace ChromaDB collection `calliope_personas` (non `vesta_users`)
- Mem0 namespace `calliope_*` separata

PRO: zero dipendenza upstream Workspace, full control divergence
CONTRO: divergence eventuale = doppia maintenance

### Path B — Import as git submodule

```bash
cd ~/Scrivania/Quill_of_Calliope
git submodule add ~/Scrivania/Workspace vesta_upstream
# Import via path absolute
sys.path.insert(0, str(Path(__file__).parent / "vesta_upstream/vesta_system1"))
from persona_tracker import PersonaTracker
```

PRO: aggiornamenti upstream automatici
CONTRO: tight coupling, Workspace changes can break Calliope

### Path C — Extract to shared library

Long-term migration: estrai persona+memory+emotional come `vesta-core` library pip-installable, sia Workspace che Calliope importano.

```bash
pip install vesta-core  # future when published
```

PRO: clean separation, vera reuse
CONTRO: setup overhead, P3 future

## Raccomandazione

**Path A** per M2-M3 (1-2 settimane dev). Veloce, full control, nessuna dipendenza Workspace state.

Migrazione **Path C** quando Quill of Calliope matura + altri progetti vorranno usare vesta-core.

## Schema mapping char ↔ persona

```python
# Vesta original
class Persona:
    user_id: str
    name: str
    emotional_state: VAD  # valence, arousal, dominance
    memory: list[MemoryEntry]
    relationships: dict[str, RelationshipState]

# Calliope adapted
class Character:  # ex-Persona
    char_id: str  # ex-user_id
    name: str
    aliases: list[str]
    type: Literal["pc", "npc", "player_of_other"]
    player: str | None  # nic se pc, alice se altro giocatore, None se npc
    scene_emotional_states: dict[scene_id, VAD]  # mood per scena attiva
    backstory: str
    traits: list[str]
    speech_pattern: SpeechPattern
    active_scenes: list[scene_id]
    relationships: dict[char_id, RelationshipState]
    memory: list[MemoryEntry]  # eventi rilevanti per char
```

Memory entries adattate:
```python
class MemoryEntry:
    char_id: str  # char che "ricorda"
    scene_id: str
    timestamp: datetime
    type: Literal["dialogue", "action", "observation", "thought", "lore_learned"]
    content: str
    importance: float  # 0-1, per retention priority
    related_chars: list[char_id]
```

## Effort stimato

- Copy + adapt persona_tracker → char_tracker: 2-3h
- Copy + adapt memory_store: 1-2h
- Adapt emotional_state per scene-level: 2-3h
- Tests + integration: 3-4h
- **Total**: 8-12h dev (~ 1-2 giorni)

## Next steps

1. Verifica esistenza file Vesta-Minerva (questa analisi è pattern-based, da confermare quando wake-up)
2. Spawn sonnet1-cops sprint M2-prep: copy files Vesta + adapt + tests basic
3. Operator review + approve before merge in Quill of Calliope src/
