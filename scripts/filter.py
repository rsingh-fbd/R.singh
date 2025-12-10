#!/usr/bin/env python3
import json
import requests
import re

# ================= CONFIG =================
SOURCE_URL    = "https://iptv-org.github.io/iptv/countries/in.m3u"
CHANNELS_JSON = "channels.json"
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
    r = requests.get(SOURCE_URL, timeout=30)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.text

def clean_channel_name(dirty_name):
    """Remove (1080p), (720p), [Not 24x7], etc. → returns clean name"""
    name = dirty_name.strip()
    # Remove anything in parentheses or brackets at the end
    name = re.sub(r"\s*[\(\[].*?[\)\]]$", "", name)
    # Remove common suffixes
    name = re.sub(r"\s*(HD|SD|4K|FHD|UHD|1080p|720p|576p|480p|360p)\s*$", "", name, flags=re.IGNORECASE)
    # Remove trailing dash/colon junk
    name = re.sub(r"[-:–—]\s*$", "", name)
    return name.strip()

def main():
    wanted = load_wanted_channels()
    print(f"Loaded {len(wanted)} channel keywords.")

    playlist = download_playlist()
    lines = playlist.splitlines()

    result = ["#EXTM3U"]
    saved = 0

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("#EXTINF:"):
            # Extract raw name after last comma
            raw_name = line.split(",")[-1].strip()
            clean_name = clean_channel_name(raw_name)
            clean_lower = clean_name.lower()

            # Match against your wanted list
           # if any(kw in clean_lower for kw in wanted):
            if clean_lower in wanted:
                # Rebuild clean EXTINF line with nice name
                new_line = line.split(",", 1)[0] + ',"' + clean_name + '"'
                result.append(new_line)
                if i+1 < len(lines) and not lines[i+1].startswith("#"):
                    result.append(lines[i+1])
                    saved += 1
        i += 1

    with open(OUTPUT_M3U, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(result) + "\n")

    print(f"Done! {saved} clean channels saved → {OUTPUT_M3U}")

if __name__ == "__main__":
    main()