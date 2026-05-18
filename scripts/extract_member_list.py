#!/usr/bin/env python3
import os
import json
import time
import argparse
import httpx
from pathlib import Path
from typing import Optional


def fetch_members(
    guild_id: str,
    token: str,
    output_path: str,
    max_retries: int = 3,
    initial_backoff: int = 5,
    max_backoff: int = 60,
) -> None:
    url = f"https://discord.com/api/v10/guilds/{guild_id}/members-search"
    headers = {"Authorization": token}
    base_params = {"query": "", "limit": 1000}

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    total_fetched = 0
    page_count = 0
    cursor: Optional[str] = None

    with open(out, "w", encoding="utf-8") as f:
        while True:
            params = {**base_params}
            if cursor:
                params["after"] = cursor

            members = _fetch_page(url, headers, params, max_retries, initial_backoff, max_backoff)
            if members is None:
                # Unrecoverable error on this page
                break
            if not members:
                break

            for m in members:
                user = m.get("user", {})
                record = {
                    "user_id": user.get("id"),
                    "username": user.get("username"),
                    "global_name": user.get("global_name"),
                    "nick": m.get("nick"),
                    "joined_at": m.get("joined_at"),
                    "roles": m.get("roles", []),
                    "avatar": user.get("avatar"),
                    "bot": user.get("bot", False),
                }
                f.write(json.dumps(record) + "\n")

            total_fetched += len(members)
            page_count += 1
            print(f"Fetched {total_fetched} members so far (page {page_count})")
            cursor = members[-1]["user"]["id"]

            if len(members) < 1000:
                break

    print(f"Completed. Total members fetched: {total_fetched}")


def _fetch_page(url, headers, params, max_retries, initial_backoff, max_backoff):
    backoff = initial_backoff
    for attempt in range(max_retries + 1):
        try:
            with httpx.Client() as client:
                resp = client.get(url, headers=headers, params=params)

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                sleep_time = int(retry_after) if retry_after else backoff
                print(f"Rate limited. Retrying in {sleep_time}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(sleep_time)
                backoff = min(backoff * 2, max_backoff)
            else:
                print(f"HTTP {resp.status_code} on attempt {attempt + 1}")
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

        except Exception as e:
            print(f"Request error: {e}")
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)

    print(f"Failed after {max_retries} retries. Aborting page.")
    return None


def main():
    parser = argparse.ArgumentParser(description="Extract Discord guild members via user token")
    parser.add_argument("--guild", default=os.getenv("KOY_GUILD_ID"), help="Guild ID")
    parser.add_argument("--token", default=os.getenv("DISCORD_USER_TOKEN"), help="User token")
    parser.add_argument("--output", default="/tmp/discord_import/members.jsonl")
    args = parser.parse_args()

    if not args.guild:
        parser.error("--guild required or set $KOY_GUILD_ID")
    if not args.token:
        parser.error("--token required or set $DISCORD_USER_TOKEN")

    fetch_members(args.guild, args.token, args.output)


if __name__ == "__main__":
    main()
