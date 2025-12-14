import json
import requests
import re

# ================= CONFIG =================
SOURCE_URL      = "https://iptv-org.github.io/iptv/countries/in.m3u"
CHANNELS_JSON   = "channels.json"
OUTPUT_M3U      = "playlist1.m3u"
EXTRA_PLAYLIST  = "backup.m3u"      # fallback playlist
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
    """Remove (1080p), (720p), [Not 24x7], HD, SD, etc."""
    name = dirty_name.strip()

    # Remove anything in parentheses or brackets
    name = re.sub(r"\s*[\(\[].*?[\)\]]$", "", name)

    # Remove suffixes like HD, 1080p, FHD
    name = re.sub(
        r"\s*(HD|SD|4K|FHD|UHD|1080p|720p|576p|480p|360p)\s*$",
        "",
        name,
        flags=re.IGNORECASE
    )

    # Remove trailing separators
    name = re.sub(r"[-:–—]\s*$", "", name)

    return name.strip()


def load_extra_playlist():
    """Load fallback playlist if some channels not found."""
    try:
        with open(EXTRA_PLAYLIST, "r", encoding="utf-8") as f:
            return f.read().splitlines()
    except:
        print("Warning: extra.m3u not found.")
        return []


def main():
    wanted = load_wanted_channels()
    print(f"Loaded {len(wanted)} channels from channels.json")

    playlist = download_playlist()
    lines = playlist.splitlines()

    result = ["#EXTM3U"]
    saved = 0
    found_channels = set()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("#EXTINF:"):
            raw_name = line.split(",")[-1].strip()
            clean_name = clean_channel_name(raw_name)
            clean_lower = clean_name.lower()

            # Exact match ONLY (unchanged)
            if clean_lower in wanted:
                found_channels.add(clean_lower)

                new_line = line.split(",", 1)[0] + ',"' + clean_name + '"'
                result.append(new_line)

                # FIX: find actual URL (skip #EXTVLCOPT etc.)
                j = i + 1
                while j < len(lines):
                    if lines[j].strip() and not lines[j].startswith("#"):
                        result.append(lines[j])
                        saved += 1
                        break
                    j += 1

        i += 1

    # ============================
    # FALLBACK SEARCH IN backup.m3u
    # (unchanged)
    # ============================
    missing = [ch for ch in wanted if ch not in found_channels]

    if missing:
        print(f"{len(missing)} channels not found in main playlist. Checking backup.m3u...")

        extra_lines = load_extra_playlist()
        j = 0

        while j < len(extra_lines):
            line = extra_lines[j].strip()

            if line.startswith("#EXTINF:"):
                raw_name = line.split(",")[-1].strip()
                clean_name = clean_channel_name(raw_name)
                clean_lower = clean_name.lower()

                if clean_lower in missing:
                    new_line = line.split(",", 1)[0] + ',"' + clean_name + '"'
                    result.append(new_line)

                    if j + 1 < len(extra_lines) and not extra_lines[j + 1].startswith("#"):
                        result.append(extra_lines[j + 1])

                    found_channels.add(clean_lower)

            j += 1

    # ============================

    with open(OUTPUT_M3U, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(result) + "\n")

    print(f"Done! {len(found_channels)} total channels saved → {OUTPUT_M3U}")


if __name__ == "__main__":
    main()