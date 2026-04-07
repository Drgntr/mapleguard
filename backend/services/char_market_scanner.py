"""
Character Market Scanner — scans, enriches, and tracks fairness of marketplace listings.

Three concurrent loops:
1. Scan loop: fetches all listed characters from explore API, upserts to DB
2. Enrich loop: enriches pending listings with detail API (arcane, ability, equipment)
3. Sale watcher: captures OrderMatched events for characters via RPC
"""

import asyncio
import json
from datetime import datetime, timezone
from math import ceil
from typing import Optional

import httpx
from sqlalchemy import select, not_, func

from config import get_settings
from db.database import async_session, CharacterMarketStatus, CharacterSaleHistory, SyncState
from services.market_data import market_data_service

settings = get_settings()

RPC_URL = "https://henesys-rpc.msu.io"
CHAR_NFT = settings.CHARACTER_NFT.lower()
MARKETPLACE = settings.MARKETPLACE_CONTRACT
ORDER_MATCHED_TOPIC_FULL = "0xd819b3bba723f50f8d3eba9453aa0d9083a236abdc78d5efd4d461064d61839"
NESO_DECIMALS = 18

ARCANE_TIERS = [
    (0, "none"),
    (60, "absolab"),
    (102, "arcane_umbra"),
    (162, "arcane_full"),
    (222, "genesis_partial"),
    (282, "genesis_full"),
    (342, "eternal_partial"),
    (402, "eternal_full"),
]


def _arcane_tier(total_force: int) -> str:
    tier = "none"
    for threshold, name in ARCANE_TIERS:
        if total_force >= threshold:
            tier = name
        else:
            break
    return tier


class CharMarketScanner:
    """Background scanner for character marketplace listings."""

    def __init__(self):
        self._running = False
        self._client: Optional[httpx.AsyncClient] = None
        self._stats = {
            "scan_runs": 0,
            "chars_scanned": 0,
            "enriched": 0,
            "sales_captured": 0,
            "errors": 0,
        }

    # ── Scan Loop ─────────────────────────────────────────────────

    async def _scan_loop(self):
        """Periodically sweep all pages of the character marketplace."""
        print("[CharScanner] Full scan loop started")
        while self._running:
            try:
                await self._full_scan()
                self._stats["scan_runs"] += 1
                print(f"[CharScanner] Scan #{self._stats['scan_runs']} complete. "
                      f"Scanned: {self._stats['chars_scanned']}")
                await asyncio.sleep(300)
            except Exception as e:
                self._stats["errors"] += 1
                print(f"[CharScanner] Scan error: {e}")
                await asyncio.sleep(60)

    async def _full_scan(self):
        """Sweep all character listing pages, upsert to DB, detect delistings."""
        first_page = await market_data_service.fetch_characters(
            page=1, page_size=135, class_filter="all_classes"
        )
        total_count = first_page[2]
        total_pages = ceil(total_count / 135) if total_count else 1
        print(f"[CharScanner] Found {total_count} chars across ~{total_pages} pages")

        all_token_ids = set()

        for pg in range(1, total_pages + 1):
            try:
                chars, is_last, _ = await market_data_service.fetch_characters(
                    page=pg, page_size=135, class_filter="all_classes"
                )
                now = datetime.now(timezone.utc).replace(tzinfo=None)

                async with async_session() as session:
                    for char in chars:
                        all_token_ids.add(char.token_id)

                        existing = await session.execute(
                            select(CharacterMarketStatus).where(
                                CharacterMarketStatus.token_id == char.token_id
                            )
                        )
                        existing = existing.scalar_one_or_none()

                        price_change = None
                        if existing and existing.price > 0 and existing.price != char.price:
                            price_change = ((char.price - existing.price) / existing.price) * 100

                        if existing:
                            existing.price = char.price
                            existing.price_change_pct = price_change
                            existing.scanned_at = now
                        else:
                            session.add(CharacterMarketStatus(
                                token_id=char.token_id,
                                asset_key=getattr(char, 'asset_key', "") or "",
                                name=char.name,
                                class_name=char.class_name,
                                job_name=char.job_name,
                                level=char.level,
                                price=char.price,
                                status="pending",
                                listed_at=now,
                            ))
                            self._stats["chars_scanned"] += 1

                    await session.commit()

                if is_last:
                    await self._mark_delistings(all_token_ids)
                    break

            except Exception as e:
                print(f"[CharScanner] Page {pg} error: {e}")
                self._stats["errors"] += 1

    async def _mark_delistings(self, current_token_ids: set):
        """Mark characters no longer listed as unlisted."""
        if not current_token_ids:
            return
        async with async_session() as session:
            stmt = select(CharacterMarketStatus).where(
                CharacterMarketStatus.status.not_in(["unlisted", "sold"]),
                not_(CharacterMarketStatus.token_id.in_(current_token_ids))
            )
            rows = (await session.execute(stmt)).scalars().all()
            for row in rows:
                row.status = "unlisted"
            if rows:
                await session.commit()
                print(f"[CharScanner] Marked {len(rows)} as unlisted")

    # ── Enrich Loop ───────────────────────────────────────────────

    async def _enrich_loop(self):
        """Continuously enrich pending listings with detail data."""
        print("[CharEnricher] Enrich loop started")
        # Higher concurrency for proxy environments: use proxy to avoid rate limits
        semaphore = asyncio.Semaphore(15 if settings.ENRICH_PROXY else 5)

        while self._running:
            try:
                async with async_session() as session:
                    stmt = select(CharacterMarketStatus).where(
                        CharacterMarketStatus.status.in_(["pending", "enriching"])
                    ).limit(30 if settings.ENRICH_PROXY else 10)
                    rows = (await session.execute(stmt)).scalars().all()

                if not rows:
                    await asyncio.sleep(10)
                    continue

                pending = []
                for row in rows:
                    row.status = "enriching"
                    async with async_session() as s2:
                        s2.add(row)
                        await s2.commit()
                    pending.append(row)

                tasks = [self._enrich_char(char_row, semaphore) for char_row in pending]
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.5 if settings.ENRICH_PROXY else 1)

            except Exception as e:
                print(f"[CharEnricher] Loop error: {e}")
                self._stats["errors"] += 1
                await asyncio.sleep(10)

    @staticmethod
    def _serialize_potential(potential) -> dict | None:
        """Serialize potential to JSON-safe dict for storage."""
        if not potential:
            return None
        if isinstance(potential, dict):
            return {k: v if isinstance(v, (int, float, str, bool, type(None), dict, list))
                    else None for k, v in potential.items()}
        return None

    async def _enrich_char(self, row: CharacterMarketStatus, semaphore: asyncio.Semaphore):
        """Enrich a single character listing with detail API data."""
        async with semaphore:
            try:
                detail = await self._enrich_fetch_detail(row.token_id)
                if not detail:
                    row.status = "failed"
                    async with async_session() as s:
                        s.add(row)
                        await s.commit()
                    return

                # Extract arcane force
                total_arcane = 0
                if detail.equipped_items:
                    for eq in detail.equipped_items:
                        if eq.item_type == "arcaneSymbol":
                            total_arcane += eq.force or 0

                tier = _arcane_tier(total_arcane)

                # Extract ability grades (from our parser extension)
                ability_grades = getattr(detail, 'ability_grades', []) or [0, 0, 0]
                if len(ability_grades) < 3:
                    ability_grades = ability_grades + [0] * (3 - len(ability_grades))
                ability_total = sum(ability_grades)

                # Extract weapon stats
                weapon_sf = 0
                weapon_pot = 0
                if detail.equipped_items:
                    for eq in detail.equipped_items:
                        if eq.slot.lower() in ("weapon", "secondweapon", "secondary"):
                            weapon_sf = eq.starforce or 0
                            weapon_pot = eq.potential_grade or 0
                            break

                # Gear score: average quality of equipped items
                gear_scores = []
                if detail.equipped_items:
                    for eq in detail.equipped_items:
                        if eq.item_type == "equip" and eq.slot:
                            sf = eq.starforce or 0
                            pot = eq.potential_grade or 0
                            bpot = 0
                            if eq.bonus_potential and isinstance(eq.bonus_potential, dict):
                                bpot = eq.bonus_potential.get("option1", {}).get("grade", 0)
                            quality = (sf * 4) + (pot * 10) + (bpot * 5)
                            gear_scores.append(quality)

                avg_gear_score = sum(gear_scores) / len(gear_scores) if gear_scores else 0

                # Collect equipped mintable item info
                equipped_items = []
                if detail.equipped_items:
                    for eq in detail.equipped_items:
                        if eq.token_id and eq.item_type == "equip":
                            bp = self._serialize_potential(eq.bonus_potential)
                            equipped_items.append({
                                "slot": eq.slot,
                                "token_id": eq.token_id,
                                "starforce": eq.starforce or 0,
                                "potential_grade": eq.potential_grade or 0,
                                "bonus_potential": bp,
                            })

                row.status = "enriched"
                row.arcane_force = total_arcane
                row.arcane_set_tier = tier
                row.ability_grades = json.dumps(ability_grades)
                row.ability_total = ability_total
                row.weapon_starforce = weapon_sf
                row.weapon_potential_grade = weapon_pot
                row.gear_score = round(avg_gear_score, 2)
                row.equipped_item_ids_json = json.dumps(equipped_items) if equipped_items else None

                async with async_session() as s:
                    s.add(row)
                    await s.commit()

                self._stats["enriched"] += 1

            except Exception as e:
                row.status = "pending"  # retry
                async with async_session() as s:
                    s.add(row)
                    await s.commit()
                print(f"[CharEnricher] Enrich error for {row.token_id}: {e}")
                self._stats["errors"] += 1

    # ── Sale Watcher ──────────────────────────────────────────────

    async def _sale_watcher_loop(self):
        """Watch RPC for character OrderMatched events and record sales."""
        print("[SaleWatcher] Loop started")
        while self._running:
            try:
                block_num = await self._get_current_block()
                if block_num <= 0:
                    await asyncio.sleep(10)
                    continue

                from_db = await self._sync_state_get("char_sale_watcher_last_block", "0")
                last_block = int(from_db) if from_db and from_db.isdigit() else 0
                if last_block == 0:
                    last_block = block_num - 500

                await self._scan_block_range(last_block + 1, block_num)
                await self._sync_state_save("char_sale_watcher_last_block", str(block_num))
                await asyncio.sleep(10)
            except Exception as e:
                print(f"[SaleWatcher] Error: {e}")
                self._stats["errors"] += 1
                await asyncio.sleep(15)

    async def _scan_block_range(self, from_block: int, to_block: int):
        """Scan a block range for character sales."""
        logs = await self._get_logs(from_block, to_block)
        if not logs:
            return

        for log in logs:
            try:
                tx_hash = log.get("transactionHash", "")
                if not tx_hash:
                    continue

                # Check duplicate
                async with async_session() as session:
                    dup = await session.execute(
                        select(func.count(CharacterSaleHistory.id)).where(
                            CharacterSaleHistory.tx_hash == tx_hash
                        )
                    )
                    if dup.scalar_one() > 0:
                        continue

                topics = log.get("topics", [])
                if len(topics) < 4:
                    continue

                seller = "0x" + topics[2][26:]
                buyer = "0x" + topics[3][26:]

                data = log["data"][2:]
                if len(data) < 256:
                    continue

                token_id = str(int(data[0:64], 16))
                nft_addr = "0x" + data[88:128].lower()
                price_wei = int(data[192:256], 16)
                price = price_wei / (10 ** NESO_DECIMALS)

                if nft_addr != CHAR_NFT:
                    continue

                # Match with enriched listing
                arc_force = 0
                abil_total = 0
                gs = 0.0
                char_class = ""
                char_level = 0

                async with async_session() as session:
                    match = await session.execute(
                        select(CharacterMarketStatus).where(
                            CharacterMarketStatus.token_id == token_id
                        )
                    )
                    match = match.scalar_one_or_none()
                    if match:
                        arc_force = match.arcane_force
                        abil_total = match.ability_total
                        gs = match.gear_score
                        char_class = match.class_name
                        char_level = match.level
                        match.status = "sold"
                        await session.commit()

                sale = CharacterSaleHistory(
                    tx_hash=tx_hash,
                    buyer=buyer,
                    seller=seller,
                    price=price,
                    token_id=token_id,
                    class_name=char_class,
                    level=char_level,
                    arcane_force=arc_force,
                    ability_total=abil_total,
                    gear_score=gs,
                )
                async with async_session() as session:
                    session.add(sale)
                    await session.commit()

                self._stats["sales_captured"] += 1

            except Exception as e:
                print(f"[SaleWatcher] Log processing error: {e}")

        if logs:
            print(f"[SaleWatcher] Processed {len(logs)} logs")

    async def _get_current_block(self) -> int:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=10)
        try:
            r = await self._client.post(RPC_URL, json={
                "jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1,
            })
            return int(r.json()["result"], 16)
        except Exception:
            return 0

    async def _enrich_fetch_detail(self, token_id: str):
        """
        Fast enrichment using direct API calls instead of the full
        market_data_service path. Uses async httpx directly, supports proxy.
        Skips enrichment of minted items — only needs character detail.
        """
        client = await self._get_enrich_client()
        headers = {
            "accept": "*/*",
            "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json",
            "origin": "https://msu.io",
            "referer": "https://msu.io/",
        }

        # 1. Try marketplace detail (has price + basic info)
        try:
            r = await client.get(
                f"{settings.MSU_API_BASE}/marketplace/characters/{token_id}",
                headers=headers,
            )
            data = r.json()
        except Exception:
            return None

        if not data or not data.get("character"):
            return None

        return CharacterListing.from_detail_api(data)

    async def _get_enrich_client(self) -> httpx.AsyncClient:
        """Get async httpx client, optionally through proxy."""
        if not self._client or self._client.is_closed:
            if settings.ENRICH_PROXY:
                print(f"[CharEnricher] Using proxy: {settings.ENRICH_PROXY}")
                self._client = httpx.AsyncClient(proxy=settings.ENRICH_PROXY, timeout=15)
            else:
                self._client = httpx.AsyncClient(timeout=15)
        return self._client

    async def _get_logs(self, from_block: int, to_block: int):
        if not self._client:
            self._client = httpx.AsyncClient(timeout=10)
        try:
            r = await self._client.post(RPC_URL, json={
                "jsonrpc": "2.0", "method": "eth_getLogs",
                "params": [{
                    "address": MARKETPLACE,
                    "topics": [ORDER_MATCHED_TOPIC_FULL],
                    "fromBlock": hex(from_block),
                    "toBlock": hex(to_block),
                }],
                "id": 1,
            }, timeout=20)
            res = r.json()
            if "error" in res:
                return []
            return res.get("result", [])
        except Exception:
            return []

    async def _sync_state_get(self, key: str, default: str = "") -> str:
        async with async_session() as session:
            row = await session.execute(select(SyncState).where(SyncState.key == key))
            s = row.scalar_one_or_none()
            return s.value if s else default

    async def _sync_state_save(self, key: str, value: str):
        async with async_session() as session:
            row = await session.execute(select(SyncState).where(SyncState.key == key))
            s = row.scalar_one_or_none()
            if s:
                s.value = value
            else:
                session.add(SyncState(key=key, value=value))
            await session.commit()

    # ── Public API ────────────────────────────────────────────────

    async def run(self):
        """Start all loops concurrently."""
        self._running = True
        try:
            await asyncio.gather(
                self._scan_loop(),
                self._enrich_loop(),
                self._sale_watcher_loop(),
            )
        except asyncio.CancelledError:
            print("[CharScanner] Shutting down...")
            self._running = False
            if self._client and not self._client.is_closed:
                await self._client.aclose()
            raise

    def get_stats(self) -> dict:
        return dict(self._stats)


# Singleton
char_market_scanner = CharMarketScanner()
