import json
from curl_cffi import requests

api_url = "https://api.msu.io/marketplace/explore/characters"
headers = {
    "accept": "*/*",
    "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "content-type": "application/json",
    "origin": "https://msu.io",
    "referer": "https://msu.io/",
}

def test_p(payload):
    try:
        r = requests.post(api_url, headers=headers, json=payload, impersonate="chrome")
        return r.status_code, len(r.json().get("characters", []))
    except Exception as e:
        return "DROP", str(e)

variants = [
    ("No class filter", {"filter": {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}}, "paginationParam": {"pageNo": 1, "pageSize": 5}}),
    ("class string", {"filter": {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}, "class": "Warrior"}, "paginationParam": {"pageNo": 1, "pageSize": 5}}),
    ("classes string", {"filter": {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}, "classes": "Warrior"}, "paginationParam": {"pageNo": 1, "pageSize": 5}}),
    ("class array", {"filter": {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}, "class": ["Warrior"]}, "paginationParam": {"pageNo": 1, "pageSize": 5}}),
    ("classes array", {"filter": {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}, "classes": ["Warrior"]}, "paginationParam": {"pageNo": 1, "pageSize": 5}}),
    ("className string", {"filter": {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}, "className": "Warrior"}, "paginationParam": {"pageNo": 1, "pageSize": 5}}),
    ("className array", {"filter": {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}, "classNames": ["Warrior"]}, "paginationParam": {"pageNo": 1, "pageSize": 5}}),
    ("jobs string", {"filter": {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}, "jobs": "Hero"}, "paginationParam": {"pageNo": 1, "pageSize": 5}}),
    ("jobs array", {"filter": {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}, "jobs": ["Hero"]}, "paginationParam": {"pageNo": 1, "pageSize": 5}}),
]

out = []
for name, payload in variants:
    code, res = test_p(payload)
    out.append(f"{name:20}: {code} | {res}")

with open("test_api_3_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
