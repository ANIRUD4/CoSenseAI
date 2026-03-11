import requests
import re

query = "coffee mug"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

r = requests.post("https://duckduckgo.com/", data={"q": query}, headers=headers)
vqd = None
match = re.search(r'vqd=([\d-]+)', r.text)
if match:
    vqd = match.group(1)
    
print(f"Token explicitly parsed: {vqd}")
if not vqd:
    print("Fallback parsing:")
    for line in r.text.splitlines():
        if "vqd=" in line:
            start = line.index("vqd=") + 4
            end = line.index("\"", start) if "\"" in line[start:] else len(line)
            vqd = line[start:end].strip("\"\'&")
            print(f"Fallback token: {vqd}")
            break

if vqd:
    params = {
        "l": "us-en",
        "o": "json",
        "q": query,
        "vqd": vqd,
        "f": ",,,",
        "p": "1"
    }
    img_search = requests.get("https://duckduckgo.com/i.js", params=params, headers=headers)
    print("i.js status code:", img_search.status_code)
    if img_search.status_code == 200:
        results = img_search.json().get("results", [])
        print(f"Found {len(results)} images!")
    else:
        print("i.js error:", img_search.text[:200])
