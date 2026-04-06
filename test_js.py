import requests
import re

url = "https://msu.io/maplestoryn/_next/static/chunks/app/(default)/gamestatus/%5Bslug%5D/%5BitemId%5D/page-844f077f575076a1.js"
r = requests.get(url)

print("Downloaded JS, size:", len(r.text))

# Find API paths
paths = re.findall(r'"(/[a-zA-Z0-9\-\_/]+search[a-zA-Z0-9\-\_/]*)"', r.text)
paths += re.findall(r'"(https://[^"]+)"', r.text)

for p in set(paths):
    if "api" in p or "search" in p or "msu-stats" in p:
        print(p)
