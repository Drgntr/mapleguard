"""
Debug script to test character combat power calculation.
Tests the CP engine with real character data.
"""
import asyncio
import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.market_data import market_data_service
from services.combat_power_engine import combat_power_engine
from models.character import CharacterListing


async def search_and_fetch(name: str) -> tuple[list[dict], CharacterListing | None]:
    """Search for a character and fetch their full details."""
    print(f"\n{'='*60}")
    print(f"Searching for character: {name}")
    print('='*60)

    # Search
    results = await market_data_service.search_navigator_characters(name)
    print(f"Search found {len(results)} result(s)")

    if not results:
        print(f"No results found for '{name}'")
        return [], None

    for r in results:
        print(f"  - {r.get('name')} | level={r.get('level')} | class={r.get('class_name')} | token_id={r.get('token_id')}")

    # Take the first match
    first = results[0]
    token_id = first.get('token_id')
    if not token_id:
        print("No token_id found, cannot fetch details")
        return results, None

    print(f"\nFetching detail for token_id: {token_id}")

    # Fetch full detail
    char_detail = await market_data_service.fetch_character_detail(token_id)

    return results, char_detail


def print_summary(name: str, char: CharacterListing):
    """Print a summary of key combat power related fields."""
    print(f"\n{'='*60}")
    print(f"SUMMARY: {name}")
    print('='*60)

    print(f"\n[BASIC INFO]")
    print(f"  Level:    {char.level}")
    print(f"  Class:    {char.class_name}")
    print(f"  Job:      {char.job_name}")
    print(f"  Token ID: {char.token_id}")
    print(f"  Name:     {char.name}")
    print(f"  Asset Key: {char.asset_key}")

    if char.ap_stats:
        print(f"\n[AP STATS KEYS]")
        ap_keys = [k for k, v in char.ap_stats.model_fields.items() if v]
        print(f"  Available fields: {ap_keys}")

        print(f"\n[AP STATS DETAIL]")
        for stat_name, stat_obj in char.ap_stats.model_dump().items():
            if stat_obj and isinstance(stat_obj, dict):
                total = stat_obj.get('total', 0)
                base = stat_obj.get('base', 0)
                enhance = stat_obj.get('enhance', 0)
                if total > 0 or base > 0 or enhance > 0:
                    print(f"  {stat_name:25s} total={total:8.1f}  base={base:8.1f}  enhance={enhance:6.1f}")
    else:
        print("\n[AP STATS] No ap_stats available")

    print(f"\n[HYPER STATS]")
    if char.hyper_stats:
        print(f"  Count: {len(char.hyper_stats)}")
        for k, v in sorted(char.hyper_stats.items()):
            print(f"    {k}: level={v}")
    else:
        print("  No hyper_stats available")

    print(f"\n[ABILITY GRADES]")
    if char.ability_grades:
        print(f"  Grades: {char.ability_grades}")
    else:
        print("  No ability_grades available")

    print(f"\n[EQUIPPED ITEMS]")
    print(f"  Count: {len(char.equipped_items)}")
    if char.equipped_items:
        first_item = char.equipped_items[0]
        print(f"\n  [FIRST ITEM STRUCTURE]")
        item_dict = first_item.model_dump()
        for k, v in item_dict.items():
            if v is not None and v != 0 and v != '' and v != []:
                if isinstance(v, dict) and len(v) > 0:
                    print(f"    {k}: (dict with {len(v)} keys)")
                    for dk, dv in list(v.items())[:5]:
                        print(f"      {dk}: {dv}")
                elif isinstance(v, list) and len(v) > 0:
                    print(f"    {k}: (list with {len(v)} items)")
                else:
                    print(f"    {k}: {v}")
            elif isinstance(v, (int, float)) and v == 0:
                # Skip zeros for cleaner output but note them
                pass

    print(f"\n[COMBAT POWER]")
    print(f"  char_cp:  {char.char_cp}")
    print(f"  char_att: {char.char_att}")
    print(f"  char_matt: {char.char_matt}")

    # Also print raw combat_power from ap_stats if available
    if char.ap_stats:
        cp = char.ap_stats.combat_power
        if cp:
            print(f"  ap_stats.combat_power: total={cp.total}, base={cp.base}, enhance={cp.enhance}")


def save_detail(name: str, char: CharacterListing):
    """Save full character detail to JSON file."""
    filename = f"{name.lower()}_detail.json"
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

    # Use model_dump with exclude_none=False to get all fields including None
    data = char.model_dump(exclude_none=False)

    # Add raw ap_stats breakdown for debugging
    if char.ap_stats:
        data['_debug_ap_stats_raw'] = char.ap_stats.model_dump()

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n[Saved full detail to: {filename}]")
    return filepath


def test_cp_calculation(name: str, char: CharacterListing):
    """Test the combat power calculation against the real CP."""
    if not char.ap_stats:
        print(f"\n[CALCULATION TEST {name}] No ap_stats available")
        return None

    real_cp = char.ap_stats.combat_power.total if char.ap_stats.combat_power else 0
    if real_cp <= 0:
        print(f"\n[CALCULATION TEST {name}] No real CP found in ap_stats")
        return None

    print(f"\n{'='*60}")
    print(f"CP CALCULATION TEST: {name}")
    print('='*60)

    ap_stats_dict = char.ap_stats.model_dump() if char.ap_stats else {}

    analysis = combat_power_engine.analyze_all_equipment(
        ap_stats=ap_stats_dict,
        equipped_items=[item.model_dump() for item in char.equipped_items],
        job_name=char.job_name or "",
        real_cp=int(real_cp),
    )

    calc_cp = analysis.get("calculated_cp", 0)
    displayed_cp = analysis.get("real_cp", 0)

    print(f"\n[RESULTS]")
    print(f" Real CP (API):     {real_cp:,}")
    print(f" Calculated CP:     {calc_cp:,}")
    print(f" Displayed CP:      {displayed_cp:,}")

    if real_cp > 0:
        error_pct = abs(calc_cp - real_cp) / real_cp * 100
        print(f" Error:             {error_pct:.2f}% ({calc_cp - real_cp:+,})")

    print(f"\n[CHARACTER STATS]")
    char_stats = analysis.get("character_stats", {})
    for k, v in char_stats.items():
        if v and isinstance(v, (int, float)) and v != 0:
            print(f" {k}: {v}")

    print(f"\n[HYPER STATS]")
    print(f" From character: {char.hyper_stats}")

    print(f"\n[ITEMS ANALYZED]")
    items = analysis.get("items", [])
    print(f" Total items: {len(items)}")
    top_items = sorted(items, key=lambda x: x.get("cp_contribution", 0), reverse=True)[:5]
    for item in top_items:
        print(f"  {item.get('slot', ''):15s} {item.get('name', 'Unknown'):30s} CP={item.get('cp_contribution', 0):,} ({item.get('cp_contribution_pct', 0):.2f}%)")

    return {
        "name": name,
        "real_cp": real_cp,
        "calculated_cp": calc_cp,
        "error_pct": abs(calc_cp - real_cp) / real_cp * 100 if real_cp > 0 else 0,
        "hyper_stats": char.hyper_stats,
        "items_count": len(items),
    }


async def main():
    print("DEBUG CP TEST - Character Combat Power Data Extraction")
    print("="*60)

    chars_to_search = ['Yeggg', 'chupper']
    all_results = {}

    for name in chars_to_search:
        search_results, char_detail = await search_and_fetch(name)
        all_results[name] = {
            'search_results': search_results,
            'char_detail': char_detail
        }

        if char_detail:
            print_summary(name, char_detail)
            save_detail(name, char_detail)
        else:
            print(f"\nNo detail fetched for {name}")

    print(f"\n{'='*60}")
    print("ALL CHARACTERS SEARCHED")
    print('='*60)

    for name, data in all_results.items():
        char = data['char_detail']
        if char:
            print(f"\n{name}: level={char.level}, class={char.class_name}, job={char.job_name}")
            print(f"  CP={char.char_cp}, ATT={char.char_att}, MATT={char.char_matt}")
            if char.ap_stats:
                print(f"  ap_stats.combat_power.total = {char.ap_stats.combat_power.total}")
            if char.hyper_stats:
                print(f"  hyper_stats keys: {list(char.hyper_stats.keys())[:5]}...")
            print(f"  equipped_items count: {len(char.equipped_items)}")
        else:
            print(f"\n{name}: NOT FOUND or no detail available")


if __name__ == "__main__":
    asyncio.run(main())