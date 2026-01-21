# script/generate_input_json.py
import json
import os

# Configuration
START = 1
END = 5000
# BASE_URL = "https://cdn-6.pishow.tv/live/{}/master.m3u8"
BASE_URL = "https://cdn-6.pishow.tv/live/{}/master.m3u8"
OUTPUT_PATH = "files/input.json"

def main():
    print(f"Generating {END - START + 1} URLs...")
    
    urls = [
        BASE_URL.format(i)
        for i in range(START, END + 1)
    ]
    
    # Make sure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(urls, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully created: {OUTPUT_PATH}")
    print(f"First URL: {urls[0]}")
    print(f"Last URL:  {urls[-1]}")
    print(f"Total items: {len(urls)}")

if __name__ == "__main__":
    main()