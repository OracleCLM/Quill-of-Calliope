# Mascot model slots

Live2D models consumed by the shared mascot shell. Select a model in the dev
dashboard with `frontend/live2d/index.html?model=<key>` (default: `mao`).

| key       | dir         | status                | git        | license |
|-----------|-------------|-----------------------|------------|---------|
| `mao`     | `mao/`      | **SHIPPABLE DEFAULT** | committed  | Live2D Free Material License + Sample Model Terms (see `mao/README.md`) |
| `koko`    | `koko/`     | dev-reference only    | gitignored | no-redistribute (private BOOTH download) |
| `tingyun` | `tingyun/`  | dev-reference only    | gitignored | fan-IP (HoYoverse) — never ship |
| `calliope`| `calliope/` | placeholder (no art)  | committed  | n/a — awaiting self-authored art |

## Policy
- **Only `mao/` is shippable / committed.** `koko/` and `tingyun/` are
  license-restricted dev-reference models for aesthetic evaluation only; they are
  excluded from git history via `.gitignore` (`models/koko/`, `models/tingyun/`)
  and **must never** enter the repo or a public/open-source build.
- Before open-source release or deployment, the shipped mascot must be `mao` (or a
  later self-authored / CC0 model), never `koko`/`tingyun`.

## Adding a dev-reference model (operator)
1. Drop the full Cubism export (`*.model3.json` + `*.moc3` + `*.physics3.json` +
   textures + `*.exp3.json`) into `models/<key>/`.
2. Add `models/<key>/` to `.gitignore` if license-restricted.
3. Register it in `frontend/live2d/app.js` → `MASCOT_MODELS` (modelUrl,
   idleMotion, expressions). Use `encodeURI()` for non-ASCII filenames.
4. If the export came from VTube Studio, the `*.exp3.json` files may not be listed
   in the `model3.json` `FileReferences.Expressions` array — add them, or
   `model.expression(name)` won't resolve.
