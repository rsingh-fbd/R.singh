#!/usr/bin/env python3
"""
Simple m3u8 accessibility checker
Reads:  files/input.json
Writes: files/working.json
"""

import json
import sys
import urllib.request
import urllib.parse
from urllib.error import HTTPError, URLError


def is_m3u8_accessible(url: str, timeout: int = 12) -> bool:
    """
    Basic check if m3u8 is reachable and looks like valid playlist
    Checks master → at least one variant/media playlist → at least one segment
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.code != 200:
                return False
            content = resp.read().decode('utf-8', errors='ignore').strip()
            if not content.startswith('#EXTM3U'):
                return False

        lines = [line.strip() for line in content.splitlines() if line.strip()]

        # Find playlist URIs (variants or segments)
        playlist_uris = []
        i = 0
        while i < len(lines):
            if lines[i].startswith('#EXT-X-STREAM-INF:') or \
               lines[i].startswith('#EXTINF:'):
                # Next line should be the URI
                if i + 1 < len(lines) and not lines[i + 1].startswith('#'):
                    playlist_uris.append(lines[i + 1])
                i += 2
                continue
            i += 1

        # If we didn't find any playlist references → probably broken
        if not playlist_uris:
            return False

        # Check at least first valid segment/playlist
        for relative_uri in playlist_uris[:3]:  # limit to first 3 attempts
            full_uri = urllib.parse.urljoin(url, relative_uri)

            req2 = urllib.request.Request(full_uri, headers=headers)
            try:
                with urllib.request.urlopen(req2, timeout=8) as resp2:
                    if resp2.code != 200:
                        continue
                    # For media playlist we could check for #EXTINF, but for speed
                    # we often accept 200 + .ts/.m3u8 as good enough
                    return True
            except (HTTPError, URLError):
                continue

        # If we reached here → couldn't get any segment/playlist
        return False

    except Exception:
        return False


def main():
    INPUT_PATH = "files/input.json"
    OUTPUT_PATH = "files/working.json"

    print("m3u8 checker started...")
    print(f"Reading: {INPUT_PATH}")

    try:
        with open(INPUT_PATH, encoding="utf-8") as f:
            urls = json.load(f)
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(urls, list):
        print("Input JSON must contain a list of strings", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(urls)} URLs to check\n")

    working = []

    for i, url in enumerate(urls, 1):
        url = url.strip()
        if not url:
            continue

        print(f"[{i:3d}/{len(urls):3d}] {url}  →  ", end="", flush=True)

        if is_m3u8_accessible(url):
            print("OK ✓")
            working.append(url)
        else:
            print("×")

    try:
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(working, f, indent=2, ensure_ascii=False)
        print(f"\nDone! Found {len(working)} working links.")
        print(f"Saved to: {OUTPUT_PATH}")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()