import sys
import asyncio

sys.path.append(r"c:\Scripts\Maple\MapleGuard\backend")
from services.market_data import market_data_service
from config import get_settings
from models.character import CharacterListing

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
            chars = [CharacterListing.from_explore_api(c) for c in data["characters"]]
            classes = list(set([c.class_name for c in chars if c.class_name]))
            if len(classes) == 1:
                out.append(f"{name:20}: FILTER SUCCESS! only {classes[0]}")
            elif len(classes) > 1:
                out.append(f"{name:20}: IGNORED")
            else:
                out.append(f"{name:20}: EMPTY")
        else:
            out.append(f"{name:20}: NO_CHARS")
    except Exception as e:
        status = getattr(getattr(e, "response", None), "status_code", "Error")
        out.append(f"{name:20}: {status}")
    return "\n".join(out)

async def main():
    base_filter = {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}}
    variations = [
        ("class lower", {**base_filter, "class": "warrior"}),
        ("class Enum", {**base_filter, "class": "Class_Warrior"}),
        ("class Enum upper", {**base_filter, "class": "CLASS_WARRIOR"}),
        ("job Enum", {**base_filter, "job": "Job_Hero"}),
        ("job lower", {**base_filter, "job": "hero"}),
        ("class name", {**base_filter, "class": "Warrior"}), # we know this 400
    ]

    out_file = []
    for name, f in variations:
        out_file.append(await test_variation(name, f))
    
    with open("test_api_9_out.txt", "w", encoding="utf-8") as file:
        file.write("\n".join(out_file))

asyncio.run(main())
