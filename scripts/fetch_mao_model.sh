#!/usr/bin/env bash
# Fetch the Mao Live2D model binaries from the official Live2D Cubism Web Samples.
#
# The human-readable config (Mao.model3.json, expressions/, motions/, physics3,
# pose3, cdi3) is committed to this repo. The heavy binaries (Mao.moc3 ~860 KB,
# Mao.2048/texture_00.png ~3 MB) exceed the 500 KB large-file guard and are
# gitignored — this script restores them so the mascot renders.
#
# Mao is a Live2D *sample* model under the Free Material License + Sample Model
# Terms (see shared/live2d_mascot/models/mao/README.md). By running this you fetch
# it directly from Live2D and accept their terms. The Cubism Core runtime is
# proprietary (vendored separately).
#
# Usage:  scripts/fetch_mao_model.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$REPO_ROOT/shared/live2d_mascot/models/mao"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "[fetch-mao] sparse-checkout Live2D/CubismWebSamples → Samples/Resources/Mao"
git clone --no-checkout --depth 1 --filter=blob:none \
    https://github.com/Live2D/CubismWebSamples.git "$TMP/cw"
cd "$TMP/cw"
git sparse-checkout init --cone
git sparse-checkout set Samples/Resources/Mao
git checkout

SRC="$TMP/cw/Samples/Resources/Mao"
mkdir -p "$DEST/Mao.2048"
cp "$SRC/Mao.moc3" "$DEST/Mao.moc3"
cp "$SRC/Mao.2048/texture_00.png" "$DEST/Mao.2048/texture_00.png"
# Refresh the JSON too (idempotent — these are also committed).
cp "$SRC"/*.json "$DEST"/ 2>/dev/null || true
cp -r "$SRC/expressions" "$SRC/motions" "$DEST"/ 2>/dev/null || true

echo "[fetch-mao] done → $DEST"
ls -la "$DEST/Mao.moc3" "$DEST/Mao.2048/texture_00.png"
