# Mao — Live2D mascot model (SHIPPABLE DEFAULT)

Official Live2D **sample model** "Mao", fetched from the Live2D Cubism Web Samples
repository. This is the default mascot for both Quill of Calliope and the shared
mascot shell (Vesta consumes the same package).

## Provenance
- Source: https://github.com/Live2D/CubismWebSamples — `Samples/Resources/Mao/`
- Fetched via sparse-checkout (only the `Mao/` folder).

## Fetching the binaries (required before first render)
The config JSON in this folder is committed, but the heavy binaries
(`Mao.moc3` ~860 KB, `Mao.2048/texture_00.png` ~3 MB) are **gitignored** — they
exceed the repo's 500 KB large-file guard. Restore them with:

```bash
scripts/fetch_mao_model.sh
```

This sparse-checkouts the Mao folder from Live2D and copies the binaries into
place. Run it on a fresh clone / in CI / before deploy.

## License — READ BEFORE REDISTRIBUTING
Mao is **not** an arbitrary open-source asset. It is governed by:

1. **Live2D Free Material License** — sample models (Haru, Hiyori, Mao, Mark,
   Natori, Ren, Rice, Wanko) are free to use, including inside distributed
   applications. See:
   https://www.live2d.com/eula/live2d-free-material-license-agreement_en.html
2. **Sample Model Terms** — per-model agreement you accept by using the model:
   https://www.live2d.com/eula/live2d-sample-model-terms_en.html
3. **Cubism Core runtime** (`live2dcubismcore.min.js`, vendored separately) is
   under the **Live2D Proprietary Software License** — NOT open source:
   https://www.live2d.com/eula/live2d-proprietary-software-license-agreement_en.html
4. **Cubism SDK Release License** is required only for *business* users with
   annual revenue ≥ 10,000,000 JPY.

> NOTE for the operator: this corrects the earlier hand-off note that described
> Mao as an "original character with clean modify+redistribute rights". Mao is a
> Live2D *sample* model — redistributable inside an app under the Free Material
> License + Sample Model Terms, but you cannot claim it as your own work, and the
> Core runtime stays proprietary. For a fully unencumbered open-source ship,
> replace Mao with a self-authored / CC0 model later.

## Files
```
mao/
  Mao.model3.json     ← modelUrl target (frontend/live2d/app.js → MASCOT_MODELS.mao)
  Mao.moc3            ← binary art (committed: Free Material License permits it)
  Mao.physics3.json
  Mao.pose3.json
  Mao.cdi3.json
  Mao.2048/texture_00.png
  expressions/exp_01..exp_08.exp3.json   ← real expression Names
  motions/                                ← Idle + TapBody groups
```

## Expressions / motions
- Expressions: `exp_01`..`exp_08` (see `data/calliope_emotion_map.yaml` for the
  emotion→slot mapping).
- Motions: `Idle`, `TapBody`. Blink (EyeBlink group) and breath (ParamBreath) are
  driven automatically by pixi-live2d-display.
- LipSync param: `ParamA`.
