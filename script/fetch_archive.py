import json
import requests
import time
import hashlib
import re
from datetime import datetime

# ================= CONFIG =================
INPUT_FILE = "movie.json"
OUTPUT_FILE = "output.json"
M3U_FILE = "vod.m3u"

SEARCH_URL = "https://archive.org/advancedsearch.php"
META_URL = "https://archive.org/metadata/{}"

# Hindi detection keywords
HINDI_KEYWORDS = []
# =========================================


def sha256(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def is_hindi_text(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in HINDI_KEYWORDS)


def is_hindi_file(filename: str) -> bool:
    name = filename.lower()
    return any(k in name for k in ["hindi", ".hin.", "_hin_", "hi."])


def search_archive(query):
    params = {
        "q": f'title:("{query}") AND mediatype:movies',
        "fl[]": ["identifier", "title", "year", "description"],
        "rows": 8,
        "output": "json"
    }
    r = requests.get(SEARCH_URL, params=params, timeout=25)
    r.raise_for_status()
    return r.json()["response"]["docs"]


def fetch_metadata(identifier):
    r = requests.get(META_URL.format(identifier), timeout=25)
    r.raise_for_status()
    return r.json()


def extract_streams(identifier, files):
    mp4, hls = [], []

    for f in files:
        name = f.get("name", "")
        if not is_hindi_file(name):
            continue

        if name.endswith(".mp4"):
            mp4.append(f"https://archive.org/download/{identifier}/{name}")
        elif name.endswith(".m3u8"):
            hls.append(f"https://archive.org/download/{identifier}/{name}")

    return mp4, hls


def detect_type(title):
    t = title.lower()
    if re.search(r"(episode|ep\.?|season|s\d+e\d+)", t):
        return "series"
    return "movie"


def extract_poster(identifier):
    return f"https://archive.org/services/img/{identifier}"


def main():
    input_data = load_json(INPUT_FILE)
    old_output = load_json(OUTPUT_FILE)

    if not input_data or "movies" not in input_data:
        print("movie.json not found or invalid")
        return

    catalog = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "language": "Hindi",
        "items": []
    }

    m3u = ["#EXTM3U"]

    for query in input_data["movies"]:
        print(f"Searching Hindi content for: {query}")
        try:
            docs = search_archive(query)
            for d in docs:
                identifier = d["identifier"]
                title = d.get("title", "")
                desc = d.get("description", "")
                year = d.get("year")

                meta = fetch_metadata(identifier)
                files = meta.get("files", [])
                language = meta.get("metadata", {}).get("language", "")

                # Strict Hindi check
                if not (
                    is_hindi_text(title)
                    or is_hindi_text(desc)
                    or is_hindi_text(language)
                ):
                    continue

                mp4, hls = extract_streams(identifier, files)

                # Skip if no Hindi playable stream
                if not mp4 and not hls:
                    continue

                item_type = detect_type(title)

                item = {
                    "type": item_type,
                    "title": title,
                    "year": year,
                    "language": "Hindi",
                    "source": "archive.org",
                    "identifier": identifier,
                    "poster": extract_poster(identifier),
                    "streams": {
                        "mp4": mp4,
                        "hls": hls
                    }
                }

                catalog["items"].append(item)

                play_url = (hls or mp4)[0]
                m3u.append(f'#EXTINF:-1 group-title="Hindi",{title}')
                m3u.append(play_url)

                time.sleep(1)

        except Exception as e:
            print("Error:", e)

    # Skip write if no change
    if old_output and sha256(old_output) == sha256(catalog):
        print("No changes detected")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    with open(M3U_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(m3u) + "\n")

    print(f"Saved {len(catalog['items'])} Hindi items")


if __name__ == "__main__":
    main()