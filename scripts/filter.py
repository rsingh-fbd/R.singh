#!/usr/bin/env python3
import json
import requests

# ================= CONFIG =================
SOURCE_URL    = "https://iptv-org.github.io/iptv/countries/in.m3u"
CHANNELS_JSON = "channels.json"      # ← your list of wanted channel names
OUTPUT_M3U    = "playlist1.m3u"
# ==========================================

def load_wanted_channels():
    try:
        with open(CHANNELS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            channels = data
        elif isinstance(data, dict) and "channels" in data:
            channels = data["channels"]
        else:
            channels = []
        return [ch.strip().lower() for ch in channels if ch.strip()]
    except Exception as e:
        print(f"Error: Cannot read {CHANNELS_JSON}: {e}")
        exit(1)

def download_playlist():
    print("Downloading latest India playlist...")
    try:
        r = requests.get(SOURCE_URL, timeout=30)
        r.raise_for_status()
        r.encoding = "utf-8"
        return r.text
    except Exception as e:
        print(f"Error: Download failed: {e}")
        exit(1)

def extract_name_from_extinf(line):
    """Gets the text after the last comma — this is the real channel name in iptv-org"""
    if ',' in line:
        return line.split(',')[-1].strip()
    return ""

def main():
    wanted = load_wanted_channels()
    print(f"Loaded {len(wanted)} channel keywords to keep.")

    playlist = download_playlist()
    lines = playlist.splitlines()

    result = ["#EXTM3U"]
    saved = 0

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("#EXTINF:"):
            # Extract real channel name (after last comma)
            channel_name = extract_name_from_extinf(line).lower()

            # Match if any keyword from channels.json is inside the name
            if any(keyword in channel_name for keyword in wanted):
                result.append(lines[i])                    # EXTINF line
                if i+1 < len(lines) and not lines[i+1].startswith("#"):
                    result.append(lines[i+1])               # URL line
                    saved += 1
                else:
                    print(f"Warning: No URL after {channel_name}")
        i += 1

    # Write final playlist
    with open(OUTPUT_M3U, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(result) + "\n")

    print(f"Done! {saved} channels saved → {OUTPUT_M3U}")

if __name__ == "__main__":
    main()