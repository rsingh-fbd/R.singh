import json
import requests
import time

INPUT_FILE = "../movie.json"
OUTPUT_FILE = "../output.json"

ARCHIVE_SEARCH_URL = "https://archive.org/advancedsearch.php"


def load_movies():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("movies", [])


def search_archive(query):
    params = {
        "q": f'title:("{query}") AND mediatype:movies',
        "fl[]": [
            "identifier",
            "title",
            "year",
            "description"
        ],
        "rows": 5,
        "page": 1,
        "output": "json"
    }

    r = requests.get(ARCHIVE_SEARCH_URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("response", {}).get("docs", [])


def build_stream_url(identifier):
    return f"https://archive.org/details/{identifier}"


def main():
    movies = load_movies()
    results = []

    for name in movies:
        print(f"Searching: {name}")
        try:
            items = search_archive(name)
            for item in items:
                results.append({
                    "search_name": name,
                    "title": item.get("title"),
                    "year": item.get("year"),
                    "identifier": item.get("identifier"),
                    "page_url": build_stream_url(item.get("identifier"))
                })
        except Exception as e:
            print(f"Error searching {name}: {e}")

        time.sleep(1)  # be polite to Archive

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(results)} items to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()