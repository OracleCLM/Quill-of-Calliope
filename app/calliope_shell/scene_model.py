import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CharacterCard:
    # Spec V2/V3 fields
    name: str = ""
    description: str = ""
    personality: str = ""
    scenario: str = ""
    first_mes: str = ""
    mes_example: str = ""
    system_prompt: str = ""
    post_history_instructions: str = ""
    alternate_greetings: List[str] = field(default_factory=list)
    character_book: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)
    extensions: Dict[str, Any] = field(default_factory=dict)

    # --------------------------------------------------------------------- #
    # Compact representation – only a single‑line persona summary
    # --------------------------------------------------------------------- #
    def compact(self, goal: str = "") -> str:
        """
        Produce a compact string suitable for injection in a scene.
        Format: "<name> — <persona line>" optionally followed by " | goal: <goal>".
        The persona line is taken from ``personality`` if present,
        otherwise from ``description`` (first line only).
        """
        source = self.personality or self.description
        # Take only the first line, strip whitespace
        persona_line = source.splitlines()[0].strip() if source else ""
        result = f"{self.name} — {persona_line}"
        if goal:
            result += f" | goal: {goal}"
        return result

    # --------------------------------------------------------------------- #
    # V3 dict conversion – round‑trip preserving unknown keys in ``extensions``
    # --------------------------------------------------------------------- #
    def to_v3_dict(self) -> Dict[str, Any]:
        base = {
            "name": self.name,
            "description": self.description,
            "personality": self.personality,
            "scenario": self.scenario,
            "first_mes": self.first_mes,
            "mes_example": self.mes_example,
            "system_prompt": self.system_prompt,
            "post_history_instructions": self.post_history_instructions,
            "alternate_greetings": list(self.alternate_greetings),
            "character_book": self.character_book,
            "tags": list(self.tags),
        }
        # Preserve unknown keys inside ``extensions`` under the key ``extensions``
        if self.extensions:
            base["extensions"] = dict(self.extensions)
        return base

    @classmethod
    def from_v3_dict(cls, data: Dict[str, Any]) -> "CharacterCard":
        extensions = data.get("extensions", {})
        # Remove the extensions key so it does not interfere with field assignment
        clean = {k: v for k, v in data.items() if k != "extensions"}
        return cls(
            name=clean.get("name", ""),
            description=clean.get("description", ""),
            personality=clean.get("personality", ""),
            scenario=clean.get("scenario", ""),
            first_mes=clean.get("first_mes", ""),
            mes_example=clean.get("mes_example", ""),
            system_prompt=clean.get("system_prompt", ""),
            post_history_instructions=clean.get("post_history_instructions", ""),
            alternate_greetings=clean.get("alternate_greetings", []),
            character_book=clean.get("character_book"),
            tags=clean.get("tags", []),
            extensions=dict(extensions),
        )

    # --------------------------------------------------------------------- #
    # Legacy YAML adapter – best‑effort mapping, unknown keys go to extensions
    # --------------------------------------------------------------------- #
    @classmethod
    def from_legacy_yaml(cls, data: Dict[str, Any]) -> "CharacterCard":
        # Work on a copy so we can pop what we map
        remaining = dict(data)

        # Mapping of legacy keys to the new spec (best‑effort)
        name = remaining.pop("name", "") or remaining.pop("slug", "")
        description = remaining.pop("backstory", "") or remaining.pop("description", "")
        personality = ""
        # Legacy may store traits or a free‑form personality field
        if "personality" in remaining:
            personality = remaining.pop("personality", "")
        elif "traits" in remaining:
            traits = remaining.pop("traits", [])
            if isinstance(traits, list):
                personality = ", ".join(traits)
        scenario = remaining.pop("scenario", "")
        first_mes = remaining.pop("first_mes", "")
        # Use the first sample quote as a mes example if present
        mes_example = ""
        if "sample_quotes" in remaining:
            quotes = remaining.pop("sample_quotes", [])
            if isinstance(quotes, list) and quotes:
                mes_example = quotes[0]
        system_prompt = remaining.pop("system_prompt", "")
        post_history_instructions = remaining.pop("post_history_instructions", "")
        alternate_greetings = remaining.pop("alternate_greetings", [])
        character_book = remaining.pop("character_book", None)
        tags = remaining.pop("tags", [])

        # Anything that is left over is considered an unknown/extension field
        extensions = remaining

        return cls(
            name=name,
            description=description,
            personality=personality,
            scenario=scenario,
            first_mes=first_mes,
            mes_example=mes_example,
            system_prompt=system_prompt,
            post_history_instructions=post_history_instructions,
            alternate_greetings=alternate_greetings,
            character_book=character_book,
            tags=tags,
            extensions=extensions,
        )


# ------------------------------------------------------------------------- #
# Scene model structures
# ------------------------------------------------------------------------- #

@dataclass
class SceneMessage:
    author: str
    content: str
    ts: Optional[str] = None
    ghost: bool = False
    source: str = "operator"


@dataclass
class SceneChat:
    id: str
    name: str
    arc: Optional[str] = None
    members: List[str] = field(default_factory=list)
    directive: str = ""
    messages: List[SceneMessage] = field(default_factory=list)
    memory_notes: List[str] = field(default_factory=list)
    created: Optional[str] = None
    updated: Optional[str] = None
    read_only: bool = False


# ------------------------------------------------------------------------- #
# Loader utilities – tolerant, never raise on missing fields
# ------------------------------------------------------------------------- #

def load_character_yaml(path: Path) -> CharacterCard:
    """
    Load a legacy character YAML file and return a ``CharacterCard``.
    The function is tolerant: missing fields are filled with defaults.
    """
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return CharacterCard.from_legacy_yaml(data)


def load_scene_yaml(path: Path) -> SceneChat:
    """
    Load a legacy scene YAML file and return a ``SceneChat``.
    The loader extracts whatever information is present and marks the
    resulting object as read‑only (legacy data must not be mutated).
    """
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Basic identifiers – fall back to filename if not present
    scene_id = data.get("scene_id")
    if not scene_id:
        scene_id = path.stem

    title = data.get("title") or data.get("name") or path.stem

    # Participants are the closest analogue to members
    participants = data.get("participants", [])
    if not isinstance(participants, list):
        participants = []

    # Timestamps – use whatever is available
    created = data.get("timestamp_start") or data.get("date_started")
    updated = data.get("timestamp_end") or data.get("last_active")

    return SceneChat(
        id=str(scene_id),
        name=str(title),
        arc=None,
        members=participants,
        directive="",
        messages=[],
        memory_notes=[],
        created=created,
        updated=updated,
        read_only=True,
    )
