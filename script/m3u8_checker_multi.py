#!/usr/bin/env python3
"""
Multithreaded m3u8 accessibility checker
Reads:  files/input.json
Writes: files/working.json
"""

import json
import sys
import urllib.request
import urllib.parse
from urllib.error import HTTPError, URLError
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock


print_lock = Lock()


def is_m3u8_accessible(url: str, timeout: int = 12) -> bool:
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.code != 200:
                return False

            content = resp.read().decode('utf-8', errors='ignore').strip()
            if not content.startswith('#EXTM3U'):
                return False

        lines = [l.strip() for l in content.splitlines() if l.strip()]
        playlist_uris = []

        i = 0
        while i < len(lines):
            if lines[i].startswith('#EXT-X-STREAM-INF:') or lines[i].startswith('#EXTINF:'):
                if i + 1 < len(lines) and not lines[i + 1].startswith('#'):
                    playlist_uris.append(lines[i + 1])
                i += 2
            else:
                i += 1

        if not playlist_uris:
            return False

        for relative_uri in playlist_uris[:3]:
            full_uri = urllib.parse.urljoin(url, relative_uri)
            try:
                req2 = urllib.request.Request(full_uri, headers=headers)
                with urllib.request.urlopen(req2, timeout=8) as r2:
                    if r2.code == 200:
                        return True
            except (HTTPError, URLError):
                continue

        return False

    except Exception:
        return False


def check_one(index, total, url):
    ok = is_m3u8_accessible(url)
    with print_lock:
        status = "OK ✓" if ok else "×"
        print(f"[{index:4d}/{total:4d}] {url}  →  {status}")
    return url if ok else None


def main():
    INPUT_PATH = "files/input.json"
    OUTPUT_PATH = "files/working.json"
    MAX_THREADS = 20   # 🔴 adjust: 10–30 recommended

    print("Multithreaded m3u8 checker started")
    print(f"Reading: {INPUT_PATH}")

    try:
        with open(INPUT_PATH, encoding="utf-8") as f:
            urls = json.load(f)
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    urls = [u.strip() for u in urls if u.strip()]
    total = len(urls)

    print(f"Found {total} URLs\n")

    working = []

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {
            executor.submit(check_one, i + 1, total, url): url
            for i, url in enumerate(urls)
        }

        for future in as_completed(futures):
            result = future.result()
            if result:
                working.append(result)

    try:
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(working, f, indent=2, ensure_ascii=False)

        print("\nDone!")
        print(f"Working links: {len(working)}")
        print(f"Saved to: {OUTPUT_PATH}")

    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()