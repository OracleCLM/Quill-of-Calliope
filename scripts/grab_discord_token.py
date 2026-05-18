#!/tmp/calliope_venv/bin/python
# scripts/grab_discord_token.py — interactive Discord token + guild/channel ID grabber
# Usage: /tmp/calliope_venv/bin/python scripts/grab_discord_token.py

import os
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROMIUM = Path.home() / ".cache/ms-playwright/chromium-1223/chrome-linux64/chrome"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

TOKEN_JS = """
() => {
  const i = document.createElement('iframe');
  document.body.appendChild(i);
  const t = i.contentWindow.localStorage?.token;
  i.remove();
  if (t) return JSON.parse(t);
  const wp = (webpackChunkdiscord_app = self.webpackChunkdiscord_app || []);
  const mods = [];
  wp.push([[Math.random()], {}, r => { for (const k in r.c) mods.push(r.c[k]); }]);
  for (const m of mods) {
    try {
      const e = m?.exports?.default ?? m?.exports;
      if (e && typeof e.getToken === 'function') return e.getToken();
    } catch {}
  }
  return null;
}
"""


def url_ids(url):
    m = re.search(r"/channels/(\d+|@me)(?:/(\d+))?", url)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def update_env(updates):
    lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    keys_seen = set()
    new_lines = []
    for line in lines:
        m = re.match(r"^([A-Z_]+)=", line)
        if m and m.group(1) in updates:
            new_lines.append(f"{m.group(1)}={updates[m.group(1)]}")
            keys_seen.add(m.group(1))
        else:
            new_lines.append(line)
    for k, v in updates.items():
        if k not in keys_seen:
            new_lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(new_lines) + "\n")
    os.chmod(ENV_PATH, 0o600)


def main():
    if not CHROMIUM.exists():
        sys.exit(f"Chromium non trovato: {CHROMIUM}")

    print("=" * 60)
    print("Quill of Calliope — Discord token grabber")
    print("=" * 60)
    print("Apro Chromium. Login Discord (QR mobile o credentials).")
    print()

    display = os.environ.get("DISPLAY", ":0")
    xauth = os.environ.get("XAUTHORITY", "")
    print(f"      DISPLAY={display} XAUTHORITY={xauth}")
    env = {"DISPLAY": display, "XAUTHORITY": xauth, "HOME": os.environ.get("HOME", "")}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=str(CHROMIUM),
            headless=False,
            env=env,
            args=["--start-maximized", "--no-sandbox"],
        )
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        page.goto("https://discord.com/login")

        print("[1/3] Login in corso… (aspetto post-login)")
        last_url = ""
        for i in range(600):  # max 10 min
            time.sleep(1)
            cur = page.url
            if cur != last_url:
                print(f"      [{i:03d}s] URL: {cur}")
                last_url = cur
            if "/channels/" in cur:
                break
        else:
            sys.exit("Timeout login (10min). Aborto.")
        print(f"      Login OK. URL: {page.url}")

        # Token extraction
        print("[2/3] Estraggo token…")
        token = None
        for _ in range(10):
            token = page.evaluate(TOKEN_JS)
            if token:
                break
            time.sleep(1)
        if not token:
            sys.exit("Token non estratto. Discord ha cambiato webpack? Fallback: DevTools manuali.")
        print(f"      Token: {token[:15]}…{token[-6:]} (len={len(token)})")

        # Guild + channel
        print()
        print("[3/3] Ora naviga a 'Kingdom of Yokai' (clicca server in sidebar),")
        print("      poi clicca sul canale 'character-sheets'.")
        print("      Quando sei sul canale, premi Enter qui.")
        input("      [Enter dopo aver cliccato character-sheets] ")

        guild_id, channel_id = url_ids(page.url)
        if not guild_id or guild_id == "@me":
            sys.exit(f"URL non valido: {page.url}. Devi essere su un canale del server.")
        if not channel_id:
            print(f"      WARN: solo guild ID rilevato ({guild_id}), no channel.")

        print(f"      KOY_GUILD_ID                 = {guild_id}")
        print(f"      CHARACTER_SHEETS_CHANNEL_ID  = {channel_id or '<vuoto>'}")

        updates = {"DISCORD_USER_TOKEN": token, "KOY_GUILD_ID": guild_id}
        if channel_id:
            updates["CHARACTER_SHEETS_CHANNEL_ID"] = channel_id
        update_env(updates)

        print()
        print(f"OK — .env aggiornato ({ENV_PATH})")
        print("Chiudo browser in 5s…")
        time.sleep(5)
        browser.close()


if __name__ == "__main__":
    main()
