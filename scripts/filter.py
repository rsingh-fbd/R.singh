#!/usr/bin/env python3
import re
import json
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

# ========================= CONFIG =========================
SOURCE_URL = "https://iptv-org.github.io/iptv/countries/in.m3u"
CHANNELS_FILE = "channels.json"        # ← must be in repo root
OUTPUT_FILE = "playlist1.m3u"
# =========================================================

def load_allowed_channels():
    try:
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            channels = json.load(f)
        # Normalize: lowercase + strip spaces
        return [ch.strip().lower() for ch in channels if ch.strip()]
    except FileNotFoundError:
        print(f"Error: {CHANNELS_FILE} not found!")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {CHANNELS_FILE}: {e}")
        exit(1)

def download_playlist():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    print("Downloading India playlist from iptv-org...")
    try:
        r = session.get(SOURCE_URL, timeout=30)
        r.raise_for_status()
        r.encoding = "utf-8"
        return r.text
    except requests.RequestException as e:
        print(f"Failed to download playlist: {e}")
        exit(1)

def main():
    allowed = load_allowed_channels()
    print(f"Loaded {len(allowed)} channel keywords to keep.")

    playlist = download_playlist()
    entries = playlist.split("#EXTINF:-1")[1:]  # skip header

    result = ["#EXTM3U"]
    matched_count = 0

    for entry in entries:
        if not entry.strip():
            continue

        block = "#EXTINF:-1" + entry
        # Extract tvg-name (most reliable)
        name_match = re.search(r'tvg-name="([^"]+)"', block, re.IGNORECASE)
        if not name_match:
            continue

        channel_name = name_match.group(1).strip().lower()

        # Match if any keyword from channels.json is inside the channel name
        if any(keyword in channel_name for keyword in allowed):
            result.append(block.rstrip())
            matched_count += 1

    # Write final playlist
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(result) + "\n")

    print(f"Done! {matched_count} channels saved → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()