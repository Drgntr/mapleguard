"""
Whale Tracker Service — Continuous marketplace intelligence.

Data sources (in priority order):
1. blockchain_indexer — real on-chain OrderMatched, Transfer, mints
2. scanner_state.json — sniper scanner results (completes indexer data)
3. SQLite DB (OrderMatchDB, NFTTransferDB) — only if indexer is unavailable
4. Live MSU marketplace API — fallback when no blockchain data exists
"""
import os
import json
import asyncio
from collections import defaultdict
from typing import Dict, List

try:
    from services.combat_power_engine import combat_power_engine
except ImportError:
    combat_power_engine = None

from services.market_data import market_data_service

STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "scripts", "scanner_state.json",
)


class WhaleTrackerService:
    def __init__(self):
        self._top_spenders: List[Dict] = []
        self._top_earners: List[Dict] = []
        self._top_farmers: List[Dict] = []
        self._top_cps: Dict[str, List[Dict]] = defaultdict(list)
        self._running = False
        self._scan_count = 0

    # ─── Spenders ─────────────────────────────────────────────────────

    async def _compute_spenders(self) -> list[dict]:
        """Buyer wallets ranked by total spent on-chain."""
        # 1. Blockchain indexer (PRIMARY — real cumulative data)
        try:
            from services.blockchain_indexer import blockchain_indexer
            idx = blockchain_indexer.get_top_spenders(10)
            if idx:
                return idx
        except Exception:
            pass

        # 2. Scanner state (sniper data with buyer wallets)
        snipes = self._load_snipes()
        if snipes:
            spenders = defaultdict(float)
            for s in snipes:
                buyer = s.get("buyer") or s.get("taker") or s.get("to_address", "")
                price = float(s.get("price", 0) or 0)
                if buyer and price > 0:
                    spenders[buyer] += price
            if spenders:
                return [{"wallet": w, "volume": round(v, 2)}
                        for w, v in sorted(spenders.items(), key=lambda x: x[1], reverse=True)[:10]]

        # 3. DB fallback
        try:
            from db.database import async_session, OrderMatchDB
            from sqlalchemy import select
            async with async_session() as db:
                res = await db.execute(select(OrderMatchDB))
                orders = res.scalars().all()
            if orders:
                spenders = defaultdict(float)
                for o in orders:
                    try:
                        spenders[o.taker] += float(o.price_wei) / 1e18
                    except Exception:
                        pass
                return [{"wallet": w, "volume": round(v, 2)}
                        for w, v in sorted(spenders.items(), key=lambda x: x[1], reverse=True)[:10]]
        except Exception:
            pass

        # 4. Marketplace proxy — nothing on-chain yet
        return await self._compute_marketplace_proxy()

    # ─── Earners (mints + sellers) ────────────────────────────────────

    async def _compute_earners(self) -> list[dict]:
        """Wallets that earned the most — sellers + mint receivers."""
        # 1. Blockchain indexer (real chain data)
        try:
            from services.blockchain_indexer import blockchain_indexer
            # Combine sellers + minters
            sellers = blockchain_indexer.get_top_earners(10)
            minters = blockchain_indexer.get_top_minters(10)

            if sellers or minters:
                # Merge: minters as a subset of earners
                merged = {}
                for e in sellers:
                    merged[e["wallet"]] = e["volume"]
                for m in minters:
                    w = m["wallet"]
                    merged[w] = merged.get(w, 0) + m["volume"]
                return [
                    {"wallet": w, "volume": round(v, 2)}
                    for w, v in sorted(merged.items(), key=lambda x: x[1], reverse=True)[:10]
                ]
        except Exception:
            pass

        # 2. Scanner state
        snipes = self._load_snipes()
        if snipes:
            earners = defaultdict(float)
            mints = defaultdict(int)
            for s in snipes:
                maker = s.get("maker") or s.get("from_address", "")
                if maker and not maker.startswith("0x00000000000000000000"):
                    earners[maker] += float(s.get("price", 0) or 0)
                elif maker and maker.startswith("0x00000000000000000000"):
                    mints[s.get("to_address", "unknown")] += 1
            for w, c in mints.items():
                earners[w] += c * 500_000
            if earners:
                return [{"wallet": w, "volume": round(v, 2)}
                        for w, v in sorted(earners.items(), key=lambda x: x[1], reverse=True)[:10]]

        # 3. DB fallback
        try:
            from db.database import async_session, OrderMatchDB, NFTTransferDB
            from sqlalchemy import select
            async with async_session() as db:
                res = await db.execute(select(OrderMatchDB))
                orders = res.scalars().all()
            if orders:
                earners = defaultdict(float)
                for o in orders:
                    try:
                        earners[o.maker] += float(o.price_wei) / 1e18
                    except Exception:
                        pass
                async with async_session() as db:
                    res = await db.execute(select(NFTTransferDB))
                    transfers = res.scalars().all()
                for t in transfers:
                    if t.from_address and t.from_address.startswith("0x00000000000000000000"):
                        earners[t.to_address] += 500_000
                return [{"wallet": w, "volume": round(v, 2)}
                        for w, v in sorted(earners.items(), key=lambda x: x[1], reverse=True)[:10]]
        except Exception:
            pass

        # 4. Marketplace proxy
        return await self._compute_marketplace_proxy()

    # ─── Bot Farmers ─────────────────────────────────────────────────

    async def _compute_bot_farmers(self) -> list[dict]:
        """Detect bot farms from on-chain transfer patterns + marketplace patterns."""
        # 1. Blockchain indexer — transfer consolidation analysis
        try:
            from services.blockchain_indexer import blockchain_indexer
            idx_farmers = blockchain_indexer.get_bot_farmers(10)
            if idx_farmers:
                return idx_farmers
        except Exception:
            pass

        # 2. DB NFTTransferDB
        try:
            from db.database import async_session, NFTTransferDB
            from sqlalchemy import select
            async with async_session() as db:
                res = await db.execute(select(NFTTransferDB))
                transfers = res.scalars().all()
            if transfers:
                consolidations = defaultdict(lambda: {"total": 0, "chars": 0, "sources": set()})
                for t in transfers:
                    if t.from_address and not t.from_address.startswith("0x00000000000000000000"):
                        consolidations[t.to_address]["total"] += 1
                        if t.nft_type == "characters":
                            consolidations[t.to_address]["chars"] += 1
                            consolidations[t.to_address]["sources"].add(t.from_address)
                farmers = []
                for w, d in consolidations.items():
                    if d["chars"] >= 3:
                        farmers.append({
                            "wallet": w, "consolidations": d["total"],
                            "char_transfers": d["chars"], "unique_sources": len(d["sources"]),
                        })
                farmers.sort(key=lambda x: x["consolidations"], reverse=True)
                return farmers[:10]
        except Exception:
            pass

        # 3. Marketplace pattern detection — many chars, similar levels
        chars, _, _ = await market_data_service.fetch_characters(page=1, page_size=200)
        if not chars:
            return []

        # Price roundness = bot pricing pattern
        price_groups = defaultdict(lambda: {"chars": [], "levels": []})
        for c in chars:
            price_round = round(getattr(c, "price", 0), -3)
            if price_round > 0:
                price_groups[price_round]["chars"].append(c)
                price_groups[price_round]["levels"].append(c.level)

        farmers = []
        for price_round, group in sorted(price_groups.items(), key=lambda x: len(x[1]["chars"]), reverse=True):
            chars_list = group["chars"]
            levels = group["levels"]
            if len(chars_list) < 3:
                continue
            avg = sum(levels) / len(levels)
            clustered = sum(1 for lv in levels if abs(lv - avg) <= 5)
            ratio = clustered / len(levels)
            if ratio >= 0.5:
                wallet_id = f"BOT_{price_round}"
                farmers.append({
                    "wallet": wallet_id,
                    "consolidations": len(chars_list),
                    "char_transfers": len(chars_list),
                    "avg_level": round(avg),
                    "level_spread": max(levels) - min(levels),
                    "clustering_ratio": round(ratio, 2),
                })

        farmers.sort(key=lambda x: x["consolidations"], reverse=True)
        return farmers[:10]

    # ─── Marketplace proxy (used when no chain data available) ────────

    async def _compute_marketplace_proxy(self) -> list[dict]:
        """Use current listings as wallet proxy when no blockchain data."""
        items = await market_data_service.fetch_all_items(max_pages=2)
        chars, _, _ = await market_data_service.fetch_characters(page=1, page_size=135)
        by_name = defaultdict(lambda: {"total_value": 0.0, "count": 0})

        for c in (chars or []):
            name = getattr(c, "nickname", None) or getattr(c, "name", None)
            if name and getattr(c, "price", 0) > 0:
                by_name[name]["total_value"] += c.price
                by_name[name]["count"] += 1

        return [{"wallet": w, "volume": round(v["total_value"], 2)}
                for w, v in sorted(by_name.items(), key=lambda x: x[1]["total_value"], reverse=True)[:10]]

    def _load_snipes(self) -> list:
        if not os.path.exists(STATE_FILE):
            return []
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f).get("snipes", [])
        except Exception:
            return []

    # ─── CP Leaders ───────────────────────────────────────────────────

    async def _compute_cp_leaders(self):
        """Scan marketplace for CP. Prioritize high-level characters."""
        chars, _, _ = await market_data_service.fetch_characters(page=1, page_size=200)
        if not chars:
            return

        candidates = sorted(
            [c for c in chars if getattr(c, "level", 0) >= 140],
            key=lambda c: c.level, reverse=True,
        )[:20]

        scanned = set()
        for cls, clist in self._top_cps.items():
            for ch in clist:
                scanned.add(ch["token_id"])

        for char in candidates:
            if char.token_id in scanned:
                continue
            scanned.add(char.token_id)

            detail = None
            try:
                detail = await market_data_service.fetch_character_detail(char.token_id)
            except Exception:
                pass

            if detail and detail.ap_stats:
                ap_data = detail.ap_stats.model_dump(by_alias=True) if hasattr(detail.ap_stats, "model_dump") else detail.ap_stats
                cp_block = ap_data.get("combat_power", {})
                cp = 0
                if isinstance(cp_block, dict):
                    cp = int(cp_block.get("total", 0) or 0)
                elif isinstance(cp_block, (int, float)):
                    cp = int(cp_block)

                if combat_power_engine:
                    try:
                        real_cp = cp
                        analysis = combat_power_engine.analyze_all_equipment(
                            ap_stats=ap_data,
                            equipped_items=[
                                {"token_id": getattr(e, "token_id", ""), "slot": getattr(e, "slot", ""),
                                 "potential_grade": getattr(e, "potential_grade", 0),
                                 "bonus_potential_grade": getattr(e, "bonus_potential_grade", 0),
                                 "starforce": getattr(e, "starforce", 0)}
                                for e in (getattr(detail, "equipped_items", []) or [])
                            ],
                            job_name=getattr(detail, "job_name", ""),
                            real_cp=real_cp,
                        )
                        cp = analysis.get("real_cp", cp)
                    except Exception:
                        pass

                cls_name = getattr(detail, "class_name", "Unknown") or "Unknown"
                char_entry = {
                    "token_id": detail.token_id, "name": detail.name,
                    "class_name": cls_name, "level": getattr(detail, "level", 0), "cp": cp,
                }
                existing = [c for c in self._top_cps.get(cls_name, []) if c["token_id"] != char.token_id]
                existing.append(char_entry)
                self._top_cps[cls_name] = sorted(existing, key=lambda x: x["cp"], reverse=True)[:10]
            else:
                cls_name = getattr(char, "class_name", "Unknown") or "Unknown"
                existing = self._top_cps.get(cls_name, [])
                if any(c["token_id"] == char.token_id for c in existing):
                    continue
                cp_proxy = int(getattr(char, "price", 0) * 2)
                char_entry = {
                    "token_id": char.token_id, "name": char.name,
                    "class_name": cls_name, "level": getattr(char, "level", 0), "cp": cp_proxy,
                }
                existing.append(char_entry)
                self._top_cps[cls_name] = sorted(existing, key=lambda x: x["cp"], reverse=True)[:10]

    # ─── Main ─────────────────────────────────────────────────────────

    async def scan_once(self):
        self._scan_count += 1
        print(f"[WhaleTracker] Scan #{self._scan_count} starting...")
        try:
            self._top_spenders = await self._compute_spenders()
            self._top_earners = await self._compute_earners()
            self._top_farmers = await self._compute_bot_farmers()
            await self._compute_cp_leaders()
            print(f"[WhaleTracker] Spend={len(self._top_spenders)}, Earn={len(self._top_earners)}, "
                  f"Farm={len(self._top_farmers)}, CP_classes={len(self._top_cps)}")
        except Exception as e:
            print(f"[WhaleTracker] Error: {e}")
            import traceback
            traceback.print_exc()

    async def run_loop(self, interval: int = 60):
        self._running = True
        print(f"[WhaleTracker] Loop started (interval={interval}s)")
        # Immediate first scan
        await self.scan_once()
        while self._running:
            await self.scan_once()
            await asyncio.sleep(interval)

    def stop(self):
        self._running = False

    def get_leaderboards(self) -> dict:
        return {
            "top_spenders": self._top_spenders,
            "top_earners": self._top_earners,
            "top_farmers": self._top_farmers,
            "top_cp": dict(self._top_cps),
        }


whale_tracker = WhaleTrackerService()
