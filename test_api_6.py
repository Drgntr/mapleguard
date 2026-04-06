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
            if len(classes) == 1 and classes[0] == "Warrior":
                out.append(f"{name:20}: FILTER SUCCESS! only {classes[0]}")
            elif len(classes) > 1:
                out.append(f"{name:20}: IGNORED (Multiple classes: {str(classes)[:50]})")
            else:
                out.append(f"{name:20}: RETURNED EMPTY or NO CLASSES")
        else:
            out.append(f"{name:20}: NO_CHARS")
    except Exception as e:
        status = getattr(getattr(e, "response", None), "status_code", "Error")
        out.append(f"{name:20}: {status}")
    return "\n".join(out)

async def main():
    base_filter = {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}}
    variations = [
        ("No class filter", base_filter),
        ("classes array", {**base_filter, "classes": ["Warrior"]}),
        ("classNames array", {**base_filter, "classNames": ["Warrior"]}),
        ("className array", {**base_filter, "className": ["Warrior"]}),
        ("classNames string", {**base_filter, "classNames": "Warrior"}),
        ("class array upper", {**base_filter, "class": ["WARRIOR"]}),
        ("classes array upper", {**base_filter, "classes": ["WARRIOR"]}),
        ("job string", {**base_filter, "job": "Hero"}),
        ("job array", {**base_filter, "job": ["Hero"]}),
        ("jobs array", {**base_filter, "jobs": ["Hero"]}),
    ]

    out_file = []
    for name, f in variations:
        out_file.append(await test_variation(name, f))
    
    with open("test_api_6_out.txt", "w", encoding="utf-8") as file:
        file.write("\n".join(out_file))

asyncio.run(main())
