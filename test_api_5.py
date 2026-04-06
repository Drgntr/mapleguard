import sys
import asyncio
import json

sys.path.append(r"c:\Scripts\Maple\MapleGuard\backend")
from services.market_data import market_data_service
from config import get_settings

settings = get_settings()

async def test_variation(name, filter_payload):
    url = f"{settings.MSU_API_BASE}/marketplace/explore/characters"
    body = {
        "filter": filter_payload,
        "paginationParam": {"pageNo": 1, "pageSize": 5},
    }
    char_headers = {
        "accept": "*/*",
        "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/json",
        "origin": "https://msu.io",
        "referer": "https://msu.io/marketplace/characters",
    }
    out = []
    try:
        data = market_data_service._post(url, body, char_headers)
        if "characters" in data:
            out.append(f"{name:20}: SUCCESS - count {len(data['characters'])}")
            if data["characters"]:
                # Print the class name of the first to ensure it's filtering
                job = data["characters"][0].get("character", {}).get("common", {}).get("job", {})
                out.append(f"  First char class: {job.get('className')}")
        else:
            out.append(f"{name:20}: NO_CHARS")
    except Exception as e:
        status = "Error"
        if hasattr(e, "response") and e.response is not None:
            status = getattr(e.response, "status_code", "UnknownCode")
        out.append(f"{name:20}: {status} {e}")
    return "\n".join(out)

async def main():
    base_filter = {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}}
    
    variations = [
        ("No class", base_filter),
        ("class string", {**base_filter, "class": "Warrior"}),
        ("class array", {**base_filter, "class": ["Warrior"]}),
        ("classes string", {**base_filter, "classes": "Warrior"}),
        ("classes array", {**base_filter, "classes": ["Warrior"]}),
        ("className string", {**base_filter, "className": "Warrior"}),
        ("classCode int", {**base_filter, "classCode": 1}),
        ("classes array Enum", {**base_filter, "classes": ["Class_Warrior"]}),
        ("class array Enum", {**base_filter, "class": ["Class_Warrior"]}),
        ("class map", {**base_filter, "class": {"class": "Warrior"}}),
    ]

    out_file = []
    for name, f in variations:
        res = await test_variation(name, f)
        out_file.append(res)
    
    with open("test_api_5_out.txt", "w", encoding="utf-8") as file:
        file.write("\n".join(out_file))

asyncio.run(main())
