import json
import requests
import time
import hashlib
import re
from datetime import datetime

INPUT_FILE = "movie.json"
OUTPUT_FILE = "output.json"
M3U_FILE = "vod.m3u"

SEARCH_URL = "https://archive.org/advancedsearch.php"
META_URL = "https://archive.org/metadata/{}"


def sha256(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def search_archive(query):
    params = {
        "q": f'title:("{query}") AND mediatype:movies',
        "fl[]": ["identifier", "title", "year", "description"],
        "rows": 8,
        "output": "json"
    }
    r = requests.get(SEARCH_URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json()["response"]["docs"]


def fetch_metadata(identifier):
    r = requests.get(META_URL.format(identifier), timeout=20)
    r.raise_for_status()
    return r.json()


def extract_streams(identifier, files):
    mp4, hls = [], []
    for f in files:
        name = f.get("name", "")
        if name.endswith(".mp4"):
            mp4.append(f"https://archive.org/download/{identifier}/{name}")
        if name.endswith(".m3u8"):
            hls.append(f"https://archive.org/download/{identifier}/{name}")
    return mp4, hls


def detect_series(title):
    return bool(re.search(r"(episode|ep\.?|season|s\d+e\d+)", title.lower()))


def detect_category(text):
    t = (text or "").lower()
    if "government" in t or "films division" in t:
        return "Documentary"
    if "education" in t:
        return "Education"
    return "Classic"


def extract_poster(identifier):
    return f"https://archive.org/services/img/{identifier}"


def main():
    input_data = load_json(INPUT_FILE)
    old_output = load_json(OUTPUT_FILE)

    catalog = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "items": []
    }

    m3u = ["#EXTM3U"]

    for query in input_data.get("movies", []):
        print("Searching:", query)
        try:
            docs = search_archive(query)
            for d in docs:
                identifier = d["identifier"]
                title = d.get("title", "")
                desc = d.get("description", "")
                year = d.get("year")

                meta = fetch_metadata(identifier)
                files = meta.get("files", [])

                mp4, hls = extract_streams(identifier, files)
                if not mp4 and not hls:
                    continue

                item_type = "series" if detect_series(title) else "movie"
                category = detect_category(desc)

                item = {
                    "type": item_type,
                    "title": title,
                    "year": year,
                    "category": category,
                    "source": "archive.org",
                    "identifier": identifier,
                    "poster": extract_poster(identifier),
                    "streams": {
                        "mp4": mp4,
                        "hls": hls
                    }
                }

                catalog["items"].append(item)

                stream_url = (hls or mp4)[0]
                m3u.append(f'#EXTINF:-1 group-title="{category}",{title}')
                m3u.append(stream_url)

                time.sleep(1)
        except Exception as e:
            print("Error:", e)

    if old_output and sha256(old_output) == sha256(catalog):
        print("No changes detected.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    with open(M3U_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(m3u) + "\n")

    print("Saved catalog and M3U successfully")


if __name__ == "__main__":
    main()