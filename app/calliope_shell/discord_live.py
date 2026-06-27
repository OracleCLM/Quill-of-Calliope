"""LIVE Discord export wrapper — invokes DiscordChatExporter (DCE) on demand.

R-CALLIOPE-ME-DISCORD-LIVE: instead of requiring a manual pre-export, wrap the
``dce`` binary (``~/.local/bin/dce`` by convention, see scripts/discord_delta_export.sh)
so the in-UI importer can pull a channel/date window at request time, then reuse the
existing ``parse_channel`` parser.

Secrets (Discord token, guild id) are read from the environment / .env — NEVER
hardcoded here. If the DCE binary is missing the caller gets a clean error and the
endpoint degrades instead of crashing.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

# Default DCE binary location (matches scripts/discord_delta_export.sh).
_DEFAULT_DCE = str(Path.home() / ".local" / "bin" / "dce")

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def _load_env_file(env_path: Path = _ENV_PATH) -> dict[str, str]:
    """Parse simple KEY=VALUE lines from a .env file. Best-effort, no deps."""
    out: dict[str, str] = {}
    if not env_path.is_file():
        return out
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            out[key.strip()] = val.strip()
    except Exception:  # noqa: BLE001
        return out
    return out


def _get_secret(key: str) -> str | None:
    """Env var takes precedence over .env file. Returns None if unset/blank."""
    val = os.environ.get(key)
    if val:
        return val
    val = _load_env_file().get(key)
    return val or None


def dce_path() -> str:
    """Resolve the DCE binary path (env override DCE_BIN, else default, else PATH)."""
    candidate = os.environ.get("DCE_BIN") or _DEFAULT_DCE
    return candidate


def dce_available(path: str | None = None) -> bool:
    """True if the DCE binary is executable / on PATH."""
    p = path or dce_path()
    if Path(p).is_file() and os.access(p, os.X_OK):
        return True
    return shutil.which(p) is not None or shutil.which("dce") is not None


class DceError(RuntimeError):
    """Raised when the DCE export cannot be performed (missing binary, missing creds, failure)."""


def build_dce_command(
    channel_ids: list[str],
    out_dir: str,
    *,
    token: str,
    after: str | None = None,
    before: str | None = None,
    binary: str | None = None,
) -> list[str]:
    """Build the DCE ``exportchannel`` argv for one-or-more channels + date window.

    DCE accepts multiple ``-c/--channel`` ids in a single ``exportchannel`` call.
    ``after``/``before`` are ISO dates (DCE ``--after``/``--before``).
    """
    bin_ = binary or dce_path()
    cmd = [bin_, "exportchannel", "-t", token, "-f", "Json", "--utc", "-o", out_dir]
    for cid in channel_ids:
        cmd += ["-c", str(cid)]
    if after:
        cmd += ["--after", after]
    if before:
        cmd += ["--before", before]
    return cmd


def run_live_export(
    channel_ids: list[str],
    out_dir: str,
    *,
    after: str | None = None,
    before: str | None = None,
    binary: str | None = None,
    token_env: str = "DISCORD_USER_TOKEN",
    timeout: int = 600,
    _runner=None,
) -> list[Path]:
    """Run DCE to export ``channel_ids`` into ``out_dir``; return produced JSON files.

    Raises ``DceError`` (never crashes) on: missing binary, missing token, no channels,
    or a non-zero DCE exit. ``_runner`` is injectable for tests (no real DCE in CI).
    """
    if not channel_ids:
        raise DceError("nessun channel_id fornito per l'export live")

    bin_ = binary or dce_path()
    if not dce_available(bin_):
        raise DceError(
            f"DiscordChatExporter (dce) non trovato: '{bin_}'. "
            "Installa DCE o esegui un export manuale e usa /scan."
        )

    token = _get_secret(token_env)
    if not token:
        raise DceError(
            f"token Discord assente ({token_env} non impostato in env/.env)"
        )

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    cmd = build_dce_command(
        channel_ids, out_dir, token=token, after=after, before=before, binary=bin_,
    )

    runner = _runner or subprocess.run
    try:
        proc = runner(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise DceError(f"impossibile eseguire dce: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise DceError(f"export DCE in timeout dopo {timeout}s") from exc

    if getattr(proc, "returncode", 0) != 0:
        stderr = (getattr(proc, "stderr", "") or "").strip()[:500]
        raise DceError(f"export DCE fallito (exit {proc.returncode}): {stderr}")

    return sorted(Path(out_dir).glob("*.json"))
