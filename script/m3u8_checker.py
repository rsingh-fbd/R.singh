import json
import urllib.request
import urllib.parse

def is_m3u8_good(url):
    try:
        with urllib.request.urlopen(url, timeout=12) as response:
            if response.code != 200:
                return False
            data = response.read().decode('utf-8', errors='ignore')
            if not data.startswith('#EXTM3U'):
                return False

            lines = data.splitlines()
            has_variants = False

            for i in range(len(lines)):
                if lines[i].startswith('#EXT-X-STREAM-INF'):
                    has_variants = True
                    if i + 1 < len(lines):
                        variant_path = lines[i + 1].strip()
                        if not variant_path:
                            continue
                        variant_url = urllib.parse.urljoin(url, variant_path)

                        try:
                            with urllib.request.urlopen(variant_url, timeout=10) as v_resp:
                                if v_resp.code != 200:
                                    return False
                                v_data = v_resp.read().decode('utf-8', errors='ignore')
                                if not v_data.startswith('#EXTM3U'):
                                    return False

                            # Check at least one segment from variant
                            segment_found = False
                            for line in v_data.splitlines():
                                if not line.startswith('#') and line.strip():
                                    seg_url = urllib.parse.urljoin(variant_url, line.strip())
                                    try:
                                        with urllib.request.urlopen(seg_url, timeout=8) as s_resp:
                                            if s_resp.code == 200:
                                                segment_found = True
                                                break
                                    except:
                                        pass
                            if not segment_found:
                                return False

            # If it's a direct media playlist (no variants)
            if not has_variants:
                segment_found = False
                for line in lines:
                    if not line.startswith('#') and line.strip():
                        seg_url = urllib.parse.urljoin(url, line.strip())
                        try:
                            with urllib.request.urlopen(seg_url, timeout=8) as s_resp:
                                if s_resp.code == 200:
                                    segment_found = True
                                    break
                        except:
                            pass
                if not segment_found:
                    return False

            return True

    except Exception:
        return False


# ─── Main ────────────────────────────────────────────────
try:
    with open('input.json', 'r', encoding='utf-8') as f:
        urls = json.load(f)
except Exception as e:
    print("Error reading input.json →", e)
    exit(1)

print(f"Checking {len(urls)} m3u8 links...\n")

working = []
for i, url in enumerate(urls, 1):
    print(f"[{i}/{len(urls)}] Checking...", url, end=" → ")
    if is_m3u8_good(url):
        print("GOOD ✓")
        working.append(url)
    else:
        print("BAD ✗")

# Save result
with open('working.json', 'w', encoding='utf-8') as f:
    json.dump(working, f, indent=2, ensure_ascii=False)

print(f"\nDone! Found {len(working)} working links.")
print("Saved to → working.json")