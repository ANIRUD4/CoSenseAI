import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("No GEMINI_API_KEY set.")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
resp = requests.get(url)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    models = resp.json().get("models", [])
    for m in models:
        print(f"Model: {m.get('name')}")
else:
    print(f"Error: {resp.text}")
