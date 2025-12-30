import json
import requests
import time
import hashlib
import re
from datetime import datetime
from urllib.parse import quote_plus

# ================= CONFIG =================
INPUT_FILE = "movie.json"
OUTPUT_FILE = "output.json"
M3U_FILE = "vod.m3u"

SEARCH_URL = "https://archive.org/advancedsearch.php"
META_URL = "https://archive.org/metadata/{}"

# Broad Hindi/devotional keywords
HINDI_KEYWORDS = [
    "hindi", "हिंदी", "dubbed", "bollywood", "devotional", "bhakti",
    "krishna", "shani", "shiva", "ram", "vaishno", "leela", "bhakt"
]

# =========================================

def sha256(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return None

def is_hindi_related(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(kw in t for kw in HINDI_KEYWORDS)

def search_archive(query: str):
    """Broader and more effective search"""
    # Escape query properly
    safe_query = quote_plus(query)
    
    # Multiple fallback queries
    queries = [
        f"{safe_query}+AND+mediatype:(movies)",  # General movies
        f"{safe_query}+AND+collection:(movies)", 
        f"{safe_query}+AND+language:(hin OR hindi OR hindustani)",
        f"{safe_query}+AND+format:(MP4 OR MPEG4)",
        safe_query  # Fallback: just the keywords
    ]
    
    for q in queries:
        params = {
            "q": q,
            "fl[]": ["identifier", "title", "description", "subject", "year", "creator", "language"],
            "rows": 15,
            "output": "json"
        }
        try:
            r = requests.get(SEARCH_URL, params=params, timeout=30)
            if r.status_code == 200:
                data = r.json()
                docs = data.get("response", {}).get("docs", [])
                if docs:
                    print(f"  → Found {len(docs)} results with query: {q}")
                    return docs
        except Exception as e:
            print(f"  → Search error: {e}")
            continue
    
    print("  → No results from any query")
    return []

def fetch_metadata(identifier: str):
    try:
        r = requests.get(META_URL.format(identifier), timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"    → Metadata error for {identifier}: {e}")
        return {}

def extract_streams(identifier: str, files: list):
    """Extract MP4 and HLS - less strict on filename"""
    mp4_links = []
    hls_links = []

    for file_info in files:
        name = file_info.get("name", "")
        if not name:
            continue

        # Accept all MP4/M3U8 - many good ones don't have "hindi" in name
        if name.lower().endswith(".mp4"):
            url = f"https://archive.org/download/{identifier}/{name}"
            mp4_links.append(url)
        elif name.lower().endswith(".m3u8"):
            url = f"https://archive.org/download/{identifier}/{name}"
            hls_links.append(url)

    return mp4_links, hls_links

def detect_type(title: str) -> str:
    t = title.lower()
    if re.search(r"\b(s\d+|season|episode|ep\.?|part)", t):
        return "series"
    return "movie"

def extract_poster(identifier: str) -> str:
    return f"https://archive.org/services/img/{identifier}"

def main():
    input_data = load_json(INPUT_FILE)
    old_output = load_json(OUTPUT_FILE)

    if not input_data or "movies" not in input_data:
        print("Error: movie.json missing or invalid format")
        return

    catalog = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "language": "Hindi",
        "total_items": 0,
        "items": []
    }

    m3u_lines = ["#EXTM3U"]
    seen_identifiers = set()

    print("Starting Hindi VOD fetch from archive.org...\n")

    for query in input_data["movies"]:
        print(f"Searching for: {query}")
        results = search_archive(query)

        for doc in results:
            identifier = doc.get("identifier")
            if not identifier or identifier in seen_identifiers:
                continue

            title = doc.get("title", "Unknown")
            description = doc.get("description", "") or ""
            language = doc.get("language", "") or ""

            # Hindi relevance check
            if not (is_hindi_related(title) or is_hindi_related(description) or is_hindi_related(str(language))):
                continue

            print(f"  → Checking: {title}")

            meta = fetch_metadata(identifier)
            files = meta.get("files", []) or []

            mp4_links, hls_links = extract_streams(identifier, files)

            if not mp4_links and not hls_links:
                print("    → No video streams found")
                continue

            play_url = (hls_links or mp4_links)[0]

            item = {
                "type": detect_type(title),
                "title": title.strip(),
                "year": doc.get("year"),
                "language": "Hindi",
                "source": "archive.org",
                "identifier": identifier,
                "poster": extract_poster(identifier),
                "streams": {"mp4": mp4_links, "hls": hls_links},
                "play_url": play_url
            }

            catalog["items"].append(item)
            seen_identifiers.add(identifier)

            m3u_lines.append(f'#EXTINF:-1 tvg-logo="{extract_poster(identifier)}" group-title="Hindi VOD",{title.strip()}')
            m3u_lines.append(play_url)

            print(f"    → Added: {title.strip()}")

            time.sleep(1.2)

    catalog["total_items"] = len(catalog["items"])

    if old_output and sha256(old_output) == sha256(catalog):
        print("\nNo changes - output unchanged")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    with open(M3U_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(m3u_lines) + "\n")

    print(f"\nSuccess! Found and saved {catalog['total_items']} items")

if __name__ == "__main__":
    main()