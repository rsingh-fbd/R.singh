import json

urls = [
    f"https://cdn-6.pishow.tv/live/{i}/master.m3u8"
    for i in range(1, 2001)
]

with open("files/input.json", "w", encoding="utf-8") as f:
    json.dump(urls, f, indent=2, ensure_ascii=False)

print("Created files/input.json with 2000 channels (1–2000)")