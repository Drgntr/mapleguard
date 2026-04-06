import json
from curl_cffi import requests

api_url = "https://api.msu.io/marketplace/explore/characters"
headers = {
    "accept": "*/*",
    "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "content-type": "application/json",
    "origin": "https://msu.io",
    "referer": "https://msu.io/marketplace/characters",
}

def test_payload(name, payload):
    try:
        r = requests.post(api_url, headers=headers, json=payload, impersonate="chrome")
        print(f"--- {name} ---")
        print("Status code:", r.status_code)
        resp = r.json()
        if "characters" in resp:
            print("Success! Characters count:", len(resp["characters"]))
            if len(resp["characters"]) > 0:
                print("First character class:", resp["characters"][0].get("character", {}).get("common", {}).get("job", {}).get("className"))
        else:
            print("Response:", json.dumps(resp)[:200])
    except Exception as e:
        print(f"Error in {name}:", e)

test_payload("String Class", {
    "filter": {"class": "Warrior"},
    "paginationParam": {"pageNo": 1, "pageSize": 5}
})

test_payload("Array Class", {
    "filter": {"class": ["Warrior"]},
    "paginationParam": {"pageNo": 1, "pageSize": 5}
})

test_payload("Array Enum Class", {
    "filter": {"class": ["Class_Warrior"]},
    "paginationParam": {"pageNo": 1, "pageSize": 5}
})

test_payload("String Enum Job", {
    "filter": {"class": "Class_Warrior", "job": "Job_Hero"},
    "paginationParam": {"pageNo": 1, "pageSize": 5}
})

test_payload("String Array Enum Job", {
    "filter": {"class": ["Class_Warrior"], "job": ["Job_Hero"]},
    "paginationParam": {"pageNo": 1, "pageSize": 5}
})
