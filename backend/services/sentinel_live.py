"""
Live Sentinel — continuously monitors NEW marketplace activity for anomalies.

Runs as a background async loop that:
1. Polls recently-listed items and detects sudden price drops / spikes
2. Detects rapid re-listings (flip attempts)
3. Detects suspicious listing volume bursts from single wallets
4. Detects underpriced listings that look like bot bait or fat-finger errors
5. Tracks new listings vs purchases to detect sniping patterns
6. Scans DB for order matches below floor (sniper detection)
7. Scans Xangle transfers for farm consolidation & same-class dumps
"""

import asyncio
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Optional
import hashlib

from services.market_data import market_data_service
from services.cache import cache_get, cache_set
from config import get_settings

settings = get_settings()

CHARACTER_FLOOR_PRICE = {
    "100": {"Archer": 250000.0, "Magician": 610000.0, "Pirate": 777777.0, "Thief": 250000.0, "Warrior": 270000.0},
    "110": {"Archer": 300000.0, "Magician": 730000.0, "Pirate": 1100000.0, "Thief": 369999.0, "Warrior": 380000.0},
    "120": {"Archer": 400000.0, "Magician": 869999.0, "Pirate": 1140000.0, "Thief": 644444.0, "Warrior": 520000.0},
    "130": {"Archer": 499999.0, "Magician": 1201652.0, "Pirate": 1599999.0, "Thief": 799999.0, "Warrior": 750000.0},
    "140": {"Archer": 829999.0, "Magician": 1300000.0, "Pirate": 1788676.0, "Thief": 1340000.0, "Warrior": 950000.0},
    "150": {"Archer": 945000.0, "Magician": 1300000.0, "Pirate": 2088887.0, "Thief": 1499782.0, "Warrior": 1299999.0},
    "160": {"Archer": 1399999.0, "Magician": 1500000.0, "Pirate": 2700000.0, "Thief": 1666666.0, "Warrior": 1999999.0},
    "170": {"Archer": 2150000.0, "Magician": 1800000.0, "Pirate": 3450000.0, "Thief": 2222222.0, "Warrior": 2499999.0},
    "180": {"Archer": 2999999.0, "Magician": 2444444.0, "Pirate": 4700000.0, "Thief": 3499999.0, "Warrior": 3699999.0},
    "190": {"Archer": 7200000.0, "Magician": 3800000.0, "Pirate": 6499000.0, "Thief": 4899500.0, "Warrior": 5555555.0},
    "200": {"Archer": 9999999.0, "Magician": 7777777.0, "Pirate": 12000000.0, "Thief": 10678982.0, "Warrior": 8888888.0},
    "210": {"Archer": 19999999.0, "Magician": 19000000.0, "Pirate": 39988888.0, "Thief": 50000000.0, "Warrior": 33333333.0},
    "220": {"Archer": None, "Magician": 198000000.0, "Pirate": None, "Thief": None, "Warrior": 258888888.0},
}


class AnomalyTypeLive:
    """Extended anomaly types for live detection."""
    PRICE_CRASH = "price_crash"
    PRICE_SPIKE = "price_spike"
    RAPID_RELIST = "rapid_relist"
    VOLUME_BURST = "volume_burst"
    FAT_FINGER = "fat_finger"
    SNIPE_PATTERN = "snipe_pattern"
    FLOOR_BREAK = "floor_break"
    SUSPICIOUS_DUMP = "bot_snipe"
    BULK_TRANSFER = "bulk_transfer"
    BOT_FARM_LISTING = "bot_farm_listing"


class LiveSentinel:
    """
    Real-time anomaly scanner that monitors new marketplace activity.
    Designed to run as a background task polling every N seconds.
    """

    def __init__(self):
        self._alerts: dict[str, dict] = {}
        self._seen_tokens: set[str] = set()
        self._seen_tx_hashes: set[str] = set()
        self._price_history: dict[str, list[dict]] = defaultdict(list)
        self._listing_history: list[dict] = []
        self._wallet_activity: dict[str, list[dict]] = defaultdict(list)
        self._floor_prices: dict[str, float] = {}
        self._running = False
        self._scan_count = 0
        self._last_scan: Optional[datetime] = None

    def _make_id(self, kind: str, *args) -> str:
        raw = f"live:{kind}:{'|'.join(str(a) for a in args)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _add_alert(self, alert: dict):
        self._alerts[alert["id"]] = alert

    # ─── Detection Algorithms ────────────────────────────────────────

    def _detect_price_anomalies(self, item: dict):
        """Detect sudden price drops or spikes for an item type."""
        name = item.get("name") or item.get("item_name", "")
        price = item.get("price", 0)
        if not name or price <= 0:
            return

        history = self._price_history[name]
        history.append({"price": price, "ts": datetime.now(timezone.utc)})

        if len(history) > 50:
            self._price_history[name] = history[-50:]
            history = self._price_history[name]

        if len(history) < 3:
            return

        recent_prices = [h["price"] for h in history[-10:]]
        avg_price = sum(recent_prices) / len(recent_prices)

        if price < avg_price * 0.4 and avg_price > 100:
            self._add_alert({
                "id": self._make_id(AnomalyTypeLive.PRICE_CRASH, name, int(price)),
                "sentinel_type": "live",
                "anomaly_type": AnomalyTypeLive.PRICE_CRASH,
                "severity": "high" if price < avg_price * 0.2 else "medium",
                "title": f"Price Crash: {name}",
                "description": (
                    f"'{name}' listed at {price:,.0f} NESO — "
                    f"{((1 - price / avg_price) * 100):.0f}% below recent average "
                    f"({avg_price:,.0f} NESO). Possible fat-finger or dump."
                ),
                "token_id": item.get("token_id", ""),
                "metadata": {
                    "current_price": price,
                    "avg_price": round(avg_price, 2),
                    "drop_pct": round((1 - price / avg_price) * 100, 1),
                    "sample_size": len(recent_prices),
                },
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })

        if price > avg_price * 3 and avg_price > 100:
            self._add_alert({
                "id": self._make_id(AnomalyTypeLive.PRICE_SPIKE, name, int(price)),
                "sentinel_type": "live",
                "anomaly_type": AnomalyTypeLive.PRICE_SPIKE,
                "severity": "medium",
                "title": f"Price Spike: {name}",
                "description": (
                    f"'{name}' listed at {price:,.0f} NESO — "
                    f"{(price / avg_price * 100):.0f}% of recent average "
                    f"({avg_price:,.0f} NESO). Possible manipulation or rare variant."
                ),
                "token_id": item.get("token_id", ""),
                "metadata": {
                    "current_price": price,
                    "avg_price": round(avg_price, 2),
                    "spike_pct": round((price / avg_price) * 100, 1),
                },
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })

    def _detect_floor_break(self, item: dict):
        """Detect listings significantly below floor price."""
        name = item.get("name") or item.get("item_name", "")
        price = item.get("price", 0)
        if not name or price <= 0:
            return

        floor = self._floor_prices.get(name)
        if floor and floor > 0 and price < floor * 0.5:
            self._add_alert({
                "id": self._make_id(AnomalyTypeLive.FLOOR_BREAK, name, item.get("token_id", "")),
                "sentinel_type": "live",
                "anomaly_type": AnomalyTypeLive.FLOOR_BREAK,
                "severity": "high",
                "title": f"Floor Break: {name}",
                "description": (
                    f"'{name}' listed at {price:,.0f} NESO — "
                    f"{((1 - price / floor) * 100):.0f}% below floor ({floor:,.0f} NESO). "
                    f"Potential snipe opportunity or error."
                ),
                "token_id": item.get("token_id", ""),
                "metadata": {
                    "current_price": price,
                    "floor_price": floor,
                    "discount_pct": round((1 - price / floor) * 100, 1),
                },
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })

    def _detect_volume_burst(self, listings: list[dict]):
        """Detect unusual volume spikes in recent listings."""
        now = datetime.now(timezone.utc)
        recent_window = timedelta(minutes=10)

        recent = [
            l for l in self._listing_history
            if l.get("ts") and (now - l["ts"]) < recent_window
        ]

        if len(recent) < 8:
            return

        wallet_counts: dict[str, int] = defaultdict(int)
        for l in recent:
            seller = l.get("seller", "unknown")
            wallet_counts[seller] += 1

        for wallet, count in wallet_counts.items():
            if count >= 5 and wallet != "unknown":
                self._add_alert({
                    "id": self._make_id(AnomalyTypeLive.VOLUME_BURST, wallet, len(recent)),
                    "sentinel_type": "live",
                    "anomaly_type": AnomalyTypeLive.VOLUME_BURST,
                    "severity": "medium" if count < 10 else "high",
                    "title": f"Volume Burst: {wallet[:8]}...",
                    "description": (
                        f"Wallet {wallet[:8]}...{wallet[-4:]} listed {count} items "
                        f"in the last 10 minutes ({len(recent)} total listings). "
                        f"Possible panic sell or bot activity."
                    ),
                    "token_id": "",
                    "metadata": {
                        "wallet": wallet,
                        "listing_count": count,
                        "total_recent": len(recent),
                        "window_minutes": 10,
                    },
                    "detected_at": now.isoformat(),
                })

    def _detect_rapid_relist(self, item: dict):
        """Detect items being rapidly re-listed (flip attempts)."""
        token_id = item.get("token_id", "")
        if not token_id:
            return

        if token_id in self._seen_tokens:
            self._add_alert({
                "id": self._make_id(AnomalyTypeLive.RAPID_RELIST, token_id),
                "sentinel_type": "live",
                "anomaly_type": AnomalyTypeLive.RAPID_RELIST,
                "severity": "low",
                "title": f"Rapid Re-list: {item.get('name', token_id[:12])}",
                "description": (
                    f"'{item.get('name', 'Unknown')}' (#{token_id[:12]}...) re-listed. "
                    f"Price: {item.get('price', 0):,.0f} NESO. "
                    f"Possible flip attempt or price adjustment."
                ),
                "token_id": token_id,
                "metadata": {
                    "price": item.get("price", 0),
                    "name": item.get("name", ""),
                },
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })

    def _detect_bulk_same_class_listings(self, listings: list[dict]):
        """Detect wallets listing many characters of the SAME class at once."""
        now = datetime.now(timezone.utc)
        chars = [l for l in listings if l.get("token_type") == "characters"]

        wallet_class_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for c in chars:
            seller = c.get("seller", "unknown")
            cls = c.get("class_name", "")
            if seller != "unknown" and cls:
                wallet_class_counts[seller][cls] += 1

        for wallet, classes in wallet_class_counts.items():
            for cls, count in classes.items():
                if count >= 3:
                    self._add_alert({
                        "id": self._make_id(AnomalyTypeLive.BOT_FARM_LISTING, wallet, cls, count),
                        "sentinel_type": "live",
                        "anomaly_type": AnomalyTypeLive.BOT_FARM_LISTING,
                        "severity": "high",
                        "title": f"Bot Farm Suspicion: {wallet[:8]}...",
                        "description": (
                            f"Wallet {wallet[:8]}...{wallet[-4:]} just listed {count} '{cls}' "
                            f"characters. High probability of bot farming accounts."
                        ),
                        "token_id": "",
                        "metadata": {"wallet": wallet, "class": cls, "count": count},
                        "detected_at": now.isoformat(),
                    })

    # ─── DB & Xangle Scanning ────────────────────────────────────────

    async def _scan_db_anomalies(self):
        """Query the SQLite database for order matches below floor + Xangle transfers."""
        now = datetime.now(timezone.utc)

        # 1. Scan OrderMatch DB for sniper detection
        await self._scan_order_matches(now)

        # 2. Scan Xangle transfers (separate try/except so one failure doesn't kill the other)
        await self._scan_xangle_transfers(now)

    async def _scan_order_matches(self, now: datetime):
        """Check recent order matches against character/item floor prices."""
        try:
            from db.database import async_session, OrderMatchDB
            from sqlalchemy import select

            async with async_session() as db:
                query = select(OrderMatchDB).order_by(OrderMatchDB.id.desc()).limit(100)
                result = await db.execute(query)
                orders = result.scalars().all()

                for o in orders:
                    try:
                        if o.tx_hash in self._seen_tx_hashes:
                            continue

                        price = float(o.price_wei) / 1e18
                        if price <= 0:
                            continue

                        self._seen_tx_hashes.add(o.tx_hash)

                        # 30-second rule: check if bought within 30s of listing
                        instant_buy = (o.timestamp or 0) - o.listing_time
                        is_snipe_30s = instant_buy >= 0 and instant_buy < 30

                        should_alert = False
                        reason = ""
                        snipe_type = ""

                        # Try as character first
                        char_detail = await market_data_service.fetch_character_detail(o.token_id)
                        if char_detail:
                            lvl = char_detail.level
                            cls = char_detail.class_name

                            if lvl < 100 and price < 50000:
                                should_alert = True
                                reason = f"Low Lv (<100) {cls} dumped at {price:,.0f} NESO (limit: 50k)"
                            else:
                                level_key = str(lvl - (lvl % 10))
                                job_prices = CHARACTER_FLOOR_PRICE.get(level_key, {})
                                job_price = job_prices.get(cls)

                                if job_price is not None and price < (job_price / 1.7):
                                    should_alert = True
                                    snipe_type = "floor_snipe"
                                    reason = f"Lv{lvl} {cls} sniped at {price:,.0f} NESO (floor: {job_price:,.0f})"
                        else:
                            # Try as item
                            item_detail = await market_data_service.fetch_item_detail(o.token_id)
                            item_name = item_detail.name if item_detail else f"Token {o.token_id[-6:]}"

                            if price < 5.0:
                                should_alert = True
                                snipe_type = "dump"
                                reason = f"Item '{item_name}' dumped for {price:.1f} NESO"
                            else:
                                # Check 30-second snipe pattern
                                if is_snipe_30s:
                                    should_alert = True
                                    snipe_type = "instant_snipe"
                                    reason = f"'{item_name}' instantly sniped at {price:,.0f} NESO ({instant_buy}s after listing)"
                                elif known_floor and known_floor > 0 and price < (known_floor * 0.4):
                                    should_alert = True
                                    reason = f"'{item_name}' sniped at {price:,.0f} NESO (-{int((1 - price / known_floor) * 100)}% of floor)"

                        if should_alert:
                            self._add_alert({
                                "id": self._make_id(AnomalyTypeLive.SUSPICIOUS_DUMP, o.tx_hash),
                                "sentinel_type": "live",
                                "anomaly_type": AnomalyTypeLive.SUSPICIOUS_DUMP,
                                "severity": "critical",
                                "title": f"Snipe/Wrong Price Buy",
                                "description": (
                                    f"Wallet {o.taker[:8]}...{o.taker[-4:]} bought below floor! "
                                    f"{reason}. Tx: {o.tx_hash[:10]}..."
                                ),
                                "token_id": o.token_id,
                                "metadata": {
                                    "price": price,
                                    "seller": o.maker,
                                    "buyer": o.taker,
                                    "tx": o.tx_hash,
                                    "reason": reason,
                                    "snipe_type": snipe_type,
                                    "time_to_purchase_sec": instant_buy,
                                },
                                "detected_at": now.isoformat(),
                            })
                    except Exception:
                        continue

        except Exception as e:
            # DB might not have any order matches yet — that's fine
            if "no such table" not in str(e).lower():
                print(f"[LiveSentinel] Order match scan error: {e}")

    async def _scan_xangle_transfers(self, now: datetime):
        """Scan Xangle explorer for bulk transfers and farm consolidation."""
        try:
            xangle_transfers = await market_data_service.fetch_xangle_transfers(size=50)
            if not xangle_transfers:
                return

            # Consolidation detection: same (sender, receiver) pair with 4+ transfers
            consolidation_pairs: dict[tuple, list] = defaultdict(list)
            for t in xangle_transfers:
                sender = t.get("ADDRSFROMINFO", {}).get("ADDR", "")
                receiver = t.get("ADDRSTOINFO", {}).get("ADDR", "")
                if sender and receiver and sender != "0x0000000000000000000000000000000000000000":
                    consolidation_pairs[(sender, receiver)].append(t)

            for (sender, receiver), txs in consolidation_pairs.items():
                if len(txs) >= 4:
                    item_names = [tx.get("TKNNM") or str(tx.get("TKNID", "")) for tx in txs]
                    unique_items = list(set(item_names))
                    names_str = ", ".join(unique_items[:3]) + ("..." if len(unique_items) > 3 else "")

                    alert_id = self._make_id(AnomalyTypeLive.BULK_TRANSFER, sender, receiver, len(txs))
                    if alert_id not in self._alerts:
                        self._add_alert({
                            "id": alert_id,
                            "sentinel_type": "live",
                            "anomaly_type": AnomalyTypeLive.BULK_TRANSFER,
                            "severity": "high",
                            "title": "Farm Consolidation",
                            "description": (
                                f"Account {sender[:8]}...{sender[-4:]} sent {len(txs)} items/chars "
                                f"to {receiver[:8]}...{receiver[-4:]}. Items: {names_str}."
                            ),
                            "token_id": "",
                            "metadata": {
                                "wallet_from": sender,
                                "wallet_to": receiver,
                                "transfer_count": len(txs),
                            },
                            "detected_at": now.isoformat(),
                        })

            # Same-class character dump detection
            await self._detect_bulk_same_class_transfers(xangle_transfers, now)

        except Exception as e:
            print(f"[LiveSentinel] Xangle scan error: {e}")

    async def _detect_bulk_same_class_transfers(self, transfers: list[dict], now: datetime):
        """Detect wallets dumping multiple characters of the same class via transfers."""
        char_transfers = [t for t in transfers if t.get("TKNCTR", {}).get("NN") == "MaplestoryCharacter"]
        if not char_transfers:
            return

        # Group by sender: count transfers and collect token IDs
        wallet_data: dict[str, list[str]] = defaultdict(list)
        for t in char_transfers:
            sender = t.get("ADDRSFROMINFO", {}).get("ADDR", "")
            if not sender or sender == "0x0000000000000000000000000000000000000000":
                continue
            token_id = str(t.get("TKNID", ""))
            if token_id:
                wallet_data[sender].append(token_id)

        for sender, token_ids in wallet_data.items():
            if len(token_ids) < 3:
                continue

            # Resolve classes (limit API calls)
            class_tallies: dict[str, int] = defaultdict(int)
            for t_id in token_ids[:10]:
                try:
                    detail = await market_data_service.fetch_character_detail(t_id)
                    if detail and detail.class_name:
                        class_tallies[detail.class_name] += 1
                except Exception:
                    continue

            for cls, count in class_tallies.items():
                if count >= 3:
                    alert_id = self._make_id("same_class_dump", sender, cls)
                    if alert_id not in self._alerts:
                        self._add_alert({
                            "id": alert_id,
                            "sentinel_type": "live",
                            "anomaly_type": AnomalyTypeLive.BOT_FARM_LISTING,
                            "severity": "high",
                            "title": "Same Class Transfer Dump",
                            "description": (
                                f"Wallet {sender[:8]}...{sender[-4:]} transferred {count} '{cls}' "
                                f"characters. High probability of bot farm liquidation."
                            ),
                            "token_id": "",
                            "metadata": {"wallet": sender, "class": cls, "count": count},
                            "detected_at": now.isoformat(),
                        })

    # ─── Scanning ────────────────────────────────────────────────────

    async def scan_once(self):
        """Run one scan cycle against current marketplace state."""
        self._scan_count += 1
        self._last_scan = datetime.now(timezone.utc)

        try:
            recent = await market_data_service.fetch_recently_listed(count=30)
        except Exception:
            return

        # Build floor prices on first scan
        if not self._floor_prices:
            await self._build_floor_index()

        new_listings = []
        for item in recent:
            token_id = item.get("token_id", "")
            if token_id and token_id not in self._seen_tokens:
                new_listings.append(item)
                self._listing_history.append({
                    **item,
                    "ts": datetime.now(timezone.utc),
                    "seller": item.get("seller", "unknown"),
                })

            self._detect_price_anomalies(item)
            self._detect_floor_break(item)
            self._detect_rapid_relist(item)

        if new_listings:
            self._detect_volume_burst(new_listings)
            self._detect_bulk_same_class_listings(new_listings)

        # Scan DB + Xangle (won't crash if tables don't exist)
        await self._scan_db_anomalies()

        # Mark all as seen
        for item in recent:
            tid = item.get("token_id", "")
            if tid:
                self._seen_tokens.add(tid)

        # Trim old listing history (keep 1 hour)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        self._listing_history = [
            l for l in self._listing_history
            if l.get("ts") and l["ts"] > cutoff
        ]

    async def _build_floor_index(self):
        """Build floor price map from current item listings."""
        try:
            items, _ = await market_data_service.fetch_items(page=1, page_size=135)
            for item in items:
                name = item.name
                if name and item.price > 0:
                    existing = self._floor_prices.get(name)
                    if existing is None or item.price < existing:
                        self._floor_prices[name] = item.price
        except Exception:
            pass

    async def run_loop(self, interval: int = 15):
        """Background loop that scans every `interval` seconds."""
        self._running = True
        while self._running:
            try:
                await self.scan_once()
            except Exception as e:
                print(f"[LiveSentinel] Scan error: {e}")
            await asyncio.sleep(interval)

    def stop(self):
        self._running = False

    # ─── API ─────────────────────────────────────────────────────────

    def get_alerts(
        self,
        severity: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        alerts = list(self._alerts.values())
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        if anomaly_type:
            alerts = [a for a in alerts if a["anomaly_type"] == anomaly_type]
        alerts.sort(key=lambda a: a.get("detected_at", ""), reverse=True)
        return alerts[:limit]

    def get_stats(self) -> dict:
        alerts = list(self._alerts.values())
        type_counts: dict[str, int] = defaultdict(int)
        sev_counts: dict[str, int] = defaultdict(int)
        for a in alerts:
            type_counts[a["anomaly_type"]] += 1
            sev_counts[a["severity"]] += 1

        return {
            "total_alerts": len(alerts),
            "by_type": dict(type_counts),
            "by_severity": {s: sev_counts.get(s, 0) for s in ["low", "medium", "high", "critical"]},
            "scan_count": self._scan_count,
            "last_scan": self._last_scan.isoformat() if self._last_scan else None,
            "tracked_tokens": len(self._seen_tokens),
            "tracked_items": len(self._price_history),
            "floor_prices_indexed": len(self._floor_prices),
        }


# Singleton
live_sentinel = LiveSentinel()
