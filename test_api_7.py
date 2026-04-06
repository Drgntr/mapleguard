import sys
import asyncio

sys.path.append(r"c:\Scripts\Maple\MapleGuard\backend")
from services.market_data import market_data_service
from config import get_settings

settings = get_settings()

async def test_variation(name, filter_payload):
    url = f"{settings.MSU_API_BASE}/marketplace/explore/characters"
    body = {
        "filter": filter_payload,
        "paginationParam": {"pageNo": 1, "pageSize": 50},
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
            out.append(f"{name:20}: SUCCESS")
        else:
            out.append(f"{name:20}: NO_CHARS")
    except Exception as e:
        status = getattr(getattr(e, "response", None), "status_code", "Error")
        out.append(f"{name:20}: {status}")
    return "\n".join(out)

async def main():
    base_filter = {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}}
    variations = [
        ("No class", base_filter),
        ("class all_classes", {**base_filter, "class": "all_classes"}),
        ("classes ints", {**base_filter, "classes": [1]}),
        ("classCodes array", {**base_filter, "classCodes": [1]}),
        ("class intArray", {**base_filter, "class": [1]}),
        ("class int", {**base_filter, "class": 1}),
        ("jobs array ints", {**base_filter, "jobs": [1]}),
        ("jobCodes array ints", {**base_filter, "jobCodes": [1]}),
    ]

    out_file = []
    for name, f in variations:
        out_file.append(await test_variation(name, f))
    
    with open("test_api_7_out.txt", "w", encoding="utf-8") as file:
        file.write("\n".join(out_file))

asyncio.run(main())
