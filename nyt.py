import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("NYT_API_KEY")

if not API_KEY:
    raise ValueError("NYT_API_KEY not found in environment")

url = f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={API_KEY}"

resp = requests.get(url)
data = resp.json()

print(json.dumps(data, indent=4))

for article in data["results"]:
    text = article["title"] + " " + article["abstract"]
    print(text)
