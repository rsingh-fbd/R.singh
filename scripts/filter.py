import re
import json
import requests

# URLs
source_url = "https://iptv-org.github.io/iptv/countries/in.m3u"
channels_file = "channels.json"
output = "playlist1.m3u"

# Load allowed channels
with open(channels_file, "r", encoding="utf-8") as f:
    allow = [x.lower() for x in json.load(f)]

# Download full India playlist
print("Downloading IN playlist...")
response = requests.get(source_url)
response.encoding = "utf-8"
data = response.text

# Split entries
entries = data.split("#EXTINF")
result = "#EXTM3U\n"

for e in entries:
    if len(e.strip()) < 5:
        continue

    block = "#EXTINF" + e

    # Get channel name
    match = re.search(r'tvg-name="([^"]+)"', block)
    if not match:
        continue

    name = match.group(1).strip().lower()

    # Compare allowed list
    for allowed in allow:
        if allowed in name:
            result += block + "\n"
            break

# Save output
with open(output, "w", encoding="utf-8") as f:
    f.write(result)

print("DONE: playlist1.m3u created ✔")