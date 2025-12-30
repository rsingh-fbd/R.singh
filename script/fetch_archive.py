import json
import requests
import time
import hashlib
import re
from datetime import datetime

# ================= CONFIG =================
INPUT_FILE = "movie.json"       # Should contain: { "movies": ["Surya Putra Shani Dev", "Shri Krishna Leela", ...] }
OUTPUT_FILE = "output.json"
M3U_FILE = "vod.m3u"

SEARCH_URL = "https://archive.org/advancedsearch.php"
META_URL = "https://archive.org/metadata/{}"

# Stronger Hindi indicators
HINDI_INDICATORS = [
    "hindi", "हिंदी", "hindī", "dubbed", "hin.", "_hin_", "hi.",
    "bollywood", "indian", "india", "devotional", "bhakti",
    "krishna", "shani", "ramayan", "mahabharat", "surya putra"
]

# =========================================


def sha256(obj):
    """Generate SHA256 hash of JSON-serializable object"""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def load_json(path):
    """Safely load JSON file"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {path} not found!")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {path}: {e}")
        return None


def is_hindi_related(text: str) -> bool:
    """Improved Hindi content detection"""
    if not text:
        return False
    t = text.lower()
    return any(indicator in t for indicator in HINDI_INDICATORS)


def is_hindi_filename(filename: str) -> bool:
    """Check if filename suggests Hindi audio/track"""
    name = filename.lower()
    return any(tag in name for tag in ["hindi", ".hin.", "_hin_", "hi.", "dubbed"])


def search_archive(query: str):
    """Search archive.org for movies matching query"""
    # Enhanced query: look for title match + movies collection
    safe_query = query.replace('"', '\\"')
    q = f'(title:("{safe_query}") OR subject:("{safe_query}")) AND collection:(movies) AND mediatype:(movies)'
    
    params = {
        "q": q,
        "fl[]": ["identifier", "title", "description", "subject", "year", "creator"],
        "rows": 10,
        "page": 1,
        "output": "json"
    }
    
    try:
        r = requests.get(SEARCH_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("response", {}).get("docs", [])
    except Exception as e:
        print(f"Search failed for '{query}': {e}")
        return []


def fetch_metadata(identifier: str):
    """Fetch full metadata for an item"""
    try:
        r = requests.get(META_URL.format(identifier), timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Metadata fetch failed for {identifier}: {e}")
        return {}


def extract_hindi_streams(identifier: str, files: list):
    """Extract only Hindi-related MP4 and HLS streams"""
    mp4_links = []
    hls_links = []

    for file_info in files:
        name = file_info.get("name", "")
        if not name:
            continue

        # Prioritize files with Hindi in name
        if not is_hindi_filename(name) and not any(ind in name.lower() for ind in ["hindi", "dubbed"]):
            # Optional: skip non-Hindi named files unless desperate
            # Remove this block if you want all .mp4/.m3u8
            continue

        format_type = file_info.get("format", "").lower()

        if name.endswith(".mp4") or format_type == "h.264":
            url = f"https://archive.org/download/{identifier}/{name}"
            mp4_links.append(url)
        elif name.endswith(".m3u8") or format_type in ["hls", "apple http live streaming"]:
            url = f"https://archive.org/download/{identifier}/{name}"
            hls_links.append(url)

    return mp4_links, hls_links


def detect_type(title: str) -> str:
    """Detect if it's a movie or series"""
    t = title.lower()
    if re.search(r"\b(s\d+|season|episode|ep\.?|part|\d{1,2}\b.*\d{4})", t):
        return "series"
    return "movie"


def extract_poster(identifier: str) -> str:
    """Get poster/thumbnail URL"""
    return f"https://archive.org/services/img/{identifier}"


def main():
    input_data = load_json(INPUT_FILE)
    old_output = load_json(OUTPUT_FILE)

    if not input_data or "movies" not in input_data:
        print("Error: movie.json is missing or doesn't have 'movies' list")
        return

    catalog = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "language": "Hindi",
        "total_items": 0,
        "items": []
    }

    m3u_lines = ["#EXTM3U"]

    seen_identifiers = set()  # Avoid duplicates

    print("Starting Hindi VOD catalog generation from archive.org...\n")

    for query in input_data["movies"]:
        print(f"Searching: {query}")
        results = search_archive(query)

        if not results:
            print(f"  → No results found\n")
            continue

        for doc in results:
            identifier = doc.get("identifier")
            if not identifier or identifier in seen_identifiers:
                continue

            title = doc.get("title", "Unknown Title")
            description = doc.get("description", "")
            subjects = doc.get("subject", [])
            if isinstance(subjects, str):
                subjects = [subjects]

            # Strong Hindi filtering
            if not (
                is_hindi_related(title) or
                is_hindi_related(description) or
                any(is_hindi_related(sub) for sub in subjects) or
                "hindi" in str(doc.get("language", "")).lower()
            ):
                continue

            print(f"  → Found potential match: {title}")

            meta = fetch_metadata(identifier)
            files = meta.get("files", [])

            mp4_links, hls_links = extract_hindi_streams(identifier, files)

            if not mp4_links and not hls_links:
                print(f"    → No playable Hindi streams found")
                continue

            # Prefer HLS if available, else MP4
            play_url = (hls_links or mp4_links)[0]

            item = {
                "type": detect_type(title),
                "title": title.strip(),
                "year": doc.get("year"),
                "description": description[:300] + "..." if len(description or "") > 300 else description,
                "language": "Hindi",
                "source": "archive.org",
                "identifier": identifier,
                "poster": extract_poster(identifier),
                "streams": {
                    "mp4": mp4_links,
                    "hls": hls_links
                },
                "play_url": play_url  # Main playback URL for M3U
            }

            catalog["items"].append(item)
            seen_identifiers.add(identifier)

            # Add to M3U
            m3u_lines.append(f'#EXTINF:-1 tvg-logo="{extract_poster(identifier)}" group-title="Hindi VOD",{title.strip()}')
            m3u_lines.append(play_url)

            print(f"    → Added: {title.strip()}\n")

            time.sleep(1.5)  # Be respectful to archive.org

    catalog["total_items"] = len(catalog["items"])

    # Only write if changed
    if old_output and sha256(old_output) == sha256(catalog):
        print("No new content — output unchanged.")
        return

    # Save JSON catalog
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    # Save M3U playlist
    with open(M3U_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(m3u_lines) + "\n")

    print(f"Success! Saved {catalog['total_items']} Hindi items to {OUTPUT_FILE} and {M3U_FILE}")


if __name__ == "__main__":
    main()