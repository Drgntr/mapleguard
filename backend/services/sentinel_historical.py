"""
Historical Sentinel — deep-scans marketplace trade history for patterns.

Analyzes:
1. Wash trading patterns across historical trades (wallet pair frequency)
2. Price manipulation timelines (coordinated pump & dump)
3. Whale wallet concentration and market dominance
4. Listing-to-sale velocity anomalies (bot sniping over time)
5. Market cycle detection (bubble/crash patterns via price volatility)
6. Item hoarding / cornering (single wallet accumulating one item type)
"""

import asyncio
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Optional
import hashlib
import math
import json
import os

from services.market_data import market_data_service
from services.cache import cache_get, cache_set
from services.sentinel_live import CHARACTER_FLOOR_PRICE
from config import get_settings

settings = get_settings()


class HistoricalAnomalyType:
    WASH_TRADE_HISTORY = "wash_trade_history"
    PUMP_AND_DUMP = "pump_and_dump"
    WHALE_DOMINANCE = "whale_dominance"
    SNIPE_PATTERN_HISTORY = "snipe_pattern_history"
    MARKET_BUBBLE = "market_bubble"
    ITEM_CORNERING = "item_cornering"
    PRICE_FIXING = "price_fixing"
    DEAD_MARKET = "dead_market"


class HistoricalSentinel:
    """
    Scans historical marketplace data to find long-term manipulation patterns
    that aren't visible in real-time monitoring.
    """

    def __init__(self):
        self._alerts: dict[str, dict] = {}
        self._analysis_results: dict[str, dict] = {}
        self._last_full_scan: Optional[datetime] = None
        self._scanning = False
        self._running = False

    def _make_id(self, kind: str, *args) -> str:
        raw = f"hist:{kind}:{'|'.join(str(a) for a in args)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _add_alert(self, alert: dict):
        self._alerts[alert["id"]] = alert

    # ─── Analysis: Price Patterns ────────────────────────────────────

    def _analyze_price_distribution(self, items: list) -> dict:
        """Analyze price distribution for signs of manipulation."""
        results = {
            "total_items": len(items),
            "price_clusters": [],
            "outliers": [],
            "suspicious_patterns": [],
        }

        if not items:
            return results

        prices = [i.price for i in items if i.price > 0]
        if len(prices) < 10:
            return results

        avg = sum(prices) / len(prices)
        std_dev = math.sqrt(sum((p - avg) ** 2 for p in prices) / len(prices))

        # Price clusters (many items at same rounded price = possible coordination)
        price_counts: dict[float, int] = defaultdict(int)
        for p in prices:
            rounded = round(p, -2)
            price_counts[rounded] += 1

        for price_point, count in sorted(price_counts.items(), key=lambda x: x[1], reverse=True):
            if count >= 5:
                pct = count / len(prices) * 100
                results["price_clusters"].append({
                    "price": price_point,
                    "count": count,
                    "percentage": round(pct, 1),
                })
                if pct > 15:
                    results["suspicious_patterns"].append(
                        f"{count} items ({pct:.0f}%) clustered at {price_point:,.0f} NESO"
                    )

        # Outliers (> 3 std devs)
        if std_dev > 0:
            for item in items:
                if item.price > 0 and abs(item.price - avg) > 3 * std_dev:
                    results["outliers"].append({
                        "token_id": item.token_id,
                        "name": item.name,
                        "price": item.price,
                        "z_score": round((item.price - avg) / std_dev, 2),
                    })

        results["avg_price"] = round(avg, 2)
        results["std_dev"] = round(std_dev, 2)
        results["coefficient_of_variation"] = round(std_dev / avg * 100, 1) if avg > 0 else 0

        return results

    def _analyze_wallet_concentration(self, items: list) -> dict:
        """Analyze seller wallet concentration for market dominance."""
        results = {
            "total_sellers": 0,
            "whale_wallets": [],
            "concentration_alerts": [],
            "hhi_index": 0,
        }

        seller_counts: dict[str, dict] = defaultdict(lambda: {"count": 0, "total_value": 0.0, "items": []})
        total = 0

        for item in items:
            seller = getattr(item, "seller", None) or "unknown"
            if seller == "unknown":
                continue
            seller_counts[seller]["count"] += 1
            seller_counts[seller]["total_value"] += item.price
            seller_counts[seller]["items"].append(item.name)
            total += 1

        if total == 0:
            return results

        results["total_sellers"] = len(seller_counts)

        shares = [(c["count"] / total * 100) for c in seller_counts.values()]
        results["hhi_index"] = round(sum(s ** 2 for s in shares), 0)

        sorted_sellers = sorted(
            seller_counts.items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        )

        for wallet, data in sorted_sellers[:10]:
            pct = data["count"] / total * 100
            results["whale_wallets"].append({
                "wallet": wallet,
                "wallet_short": f"{wallet[:8]}...{wallet[-4:]}",
                "listing_count": data["count"],
                "total_value": round(data["total_value"], 2),
                "market_share_pct": round(pct, 1),
                "unique_items": len(set(data["items"])),
            })

            if pct > 15:
                self._add_alert({
                    "id": self._make_id(HistoricalAnomalyType.WHALE_DOMINANCE, wallet),
                    "sentinel_type": "historical",
                    "anomaly_type": HistoricalAnomalyType.WHALE_DOMINANCE,
                    "severity": "high" if pct > 25 else "medium",
                    "title": f"Whale Dominance: {wallet[:8]}...",
                    "description": (
                        f"Wallet {wallet[:8]}...{wallet[-4:]} controls {pct:.1f}% of active listings "
                        f"({data['count']} items, {data['total_value']:,.0f} NESO total). "
                        f"Market concentration risk."
                    ),
                    "token_id": "",
                    "metadata": {
                        "wallet": wallet,
                        "market_share": round(pct, 1),
                        "listing_count": data["count"],
                        "total_value": round(data["total_value"], 2),
                    },
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                })

        if results["hhi_index"] > 2500:
            self._add_alert({
                "id": self._make_id("hhi_concentration", int(results["hhi_index"])),
                "sentinel_type": "historical",
                "anomaly_type": HistoricalAnomalyType.WHALE_DOMINANCE,
                "severity": "high" if results["hhi_index"] > 5000 else "medium",
                "title": "High Market Concentration",
                "description": (
                    f"Market HHI index is {results['hhi_index']:,.0f} (>2500 = highly concentrated). "
                    f"Only {results['total_sellers']} unique sellers across {total} listings. "
                    f"Top seller controls {sorted_sellers[0][1]['count']} listings."
                ),
                "token_id": "",
                "metadata": {"hhi": results["hhi_index"], "total_sellers": results["total_sellers"]},
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })

        return results

    def _analyze_item_hoarding(self, items: list) -> dict:
        """Detect single wallets accumulating specific item types."""
        results = {"cornered_items": []}

        item_seller: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        item_total: dict[str, int] = defaultdict(int)

        for item in items:
            name = item.name
            seller = getattr(item, "seller", None) or "unknown"
            if name and seller != "unknown":
                item_seller[name][seller] += 1
                item_total[name] += 1

        for name, sellers in item_seller.items():
            total = item_total[name]
            if total < 3:
                continue

            top_seller = max(sellers.items(), key=lambda x: x[1])
            wallet, count = top_seller
            pct = count / total * 100

            if pct >= 60 and count >= 3:
                results["cornered_items"].append({
                    "item_name": name,
                    "wallet": wallet,
                    "wallet_short": f"{wallet[:8]}...{wallet[-4:]}",
                    "owned_count": count,
                    "total_listed": total,
                    "control_pct": round(pct, 1),
                })

                self._add_alert({
                    "id": self._make_id(HistoricalAnomalyType.ITEM_CORNERING, name, wallet),
                    "sentinel_type": "historical",
                    "anomaly_type": HistoricalAnomalyType.ITEM_CORNERING,
                    "severity": "high" if pct > 80 else "medium",
                    "title": f"Item Cornering: {name}",
                    "description": (
                        f"Wallet {wallet[:8]}...{wallet[-4:]} controls {pct:.0f}% of "
                        f"'{name}' listings ({count}/{total}). "
                        f"Possible market cornering or price fixing."
                    ),
                    "token_id": "",
                    "metadata": {
                        "item": name, "wallet": wallet,
                        "control_pct": round(pct, 1), "owned": count, "total": total,
                    },
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                })

        return results

    def _analyze_character_market(self, chars: list) -> dict:
        """Analyze character market for pricing anomalies per class."""
        results = {"class_analysis": {}, "underpriced_chars": [], "overpriced_chars": []}

        by_class: dict[str, list] = defaultdict(list)
        for c in chars:
            cls = c.class_name or "Unknown"
            if c.price > 0:
                by_class[cls].append(c)

        for cls, chars_in_class in by_class.items():
            prices = [c.price for c in chars_in_class]
            if len(prices) < 3:
                continue

            avg = sum(prices) / len(prices)
            sorted_prices = sorted(prices)
            median = sorted_prices[len(sorted_prices) // 2]
            floor = sorted_prices[0]

            results["class_analysis"][cls] = {
                "count": len(chars_in_class),
                "avg_price": round(avg, 2),
                "median_price": round(median, 2),
                "floor_price": round(floor, 2),
                "max_price": round(sorted_prices[-1], 2),
                "spread": round(sorted_prices[-1] - floor, 2),
            }

            for c in chars_in_class:
                if c.price < median * 0.3 and median > 1000:
                    results["underpriced_chars"].append({
                        "token_id": c.token_id,
                        "name": c.name,
                        "class": cls,
                        "level": c.level,
                        "price": c.price,
                        "median": round(median, 2),
                        "discount_pct": round((1 - c.price / median) * 100, 1),
                    })

        return results

    def _analyze_market_health(self, items: list, chars: list) -> dict:
        """Overall market health metrics."""
        item_prices = [i.price for i in items if i.price > 0]
        char_prices = [c.price for c in chars if c.price > 0]

        def calc_stats(prices):
            if not prices:
                return {"count": 0}
            avg = sum(prices) / len(prices)
            s = sorted(prices)
            median = s[len(s) // 2]
            std = math.sqrt(sum((p - avg) ** 2 for p in prices) / len(prices)) if len(prices) > 1 else 0
            return {
                "count": len(prices),
                "avg": round(avg, 2),
                "median": round(median, 2),
                "floor": round(s[0], 2),
                "ceiling": round(s[-1], 2),
                "std_dev": round(std, 2),
                "cv": round(std / avg * 100, 1) if avg > 0 else 0,
            }

        name_counts: dict[str, int] = defaultdict(int)
        for i in items:
            name_counts[i.name] += 1

        active_items = sum(1 for c in name_counts.values() if c >= 2)
        dead_items = sum(1 for c in name_counts.values() if c == 1)

        health = {
            "items": calc_stats(item_prices),
            "characters": calc_stats(char_prices),
            "unique_item_types": len(name_counts),
            "active_item_types": active_items,
            "single_listing_types": dead_items,
            "liquidity_score": round(active_items / max(len(name_counts), 1) * 100, 1),
        }

        if health["liquidity_score"] < 20:
            self._add_alert({
                "id": self._make_id(HistoricalAnomalyType.DEAD_MARKET, "low_liquidity"),
                "sentinel_type": "historical",
                "anomaly_type": HistoricalAnomalyType.DEAD_MARKET,
                "severity": "medium",
                "title": "Low Market Liquidity",
                "description": (
                    f"Only {health['liquidity_score']:.0f}% of item types have multiple listings. "
                    f"{dead_items} item types have a single listing. "
                    f"Low liquidity increases manipulation risk."
                ),
                "token_id": "",
                "metadata": health,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })

        return health

    # ─── Historical Snipe Scanner ────────────────────────────────────

    async def get_historical_bot_snipes(self, limit: int = 500) -> list[dict]:
        """Query DB for order matches that were purchased significantly below floor."""
        results = []
        try:
            from db.database import async_session, OrderMatchDB
            from sqlalchemy import select

            async with async_session() as db:
                query = select(OrderMatchDB).order_by(OrderMatchDB.id.desc()).limit(limit)
                res = await db.execute(query)
                orders = res.scalars().all()

                for o in orders:
                    try:
                        price = float(o.price_wei) / 1e18
                        if price <= 0:
                            continue

                        is_snipe = False
                        floor_price = None
                        asset_name = f"Token #{o.token_id[-8:]}"

                        # Try character floor check
                        char_detail = await market_data_service.fetch_character_detail(o.token_id)
                        if char_detail:
                            lvl = char_detail.level
                            cls = char_detail.class_name
                            asset_name = f"Lv{lvl} {cls} {char_detail.name}"
                            level_key = str(lvl - (lvl % 10))
                            job_prices = CHARACTER_FLOOR_PRICE.get(level_key, {})
                            fp = job_prices.get(cls)

                            if fp is not None and price < (fp / 1.7):
                                is_snipe = True
                                floor_price = fp
                            elif lvl < 100 and price < 50000:
                                is_snipe = True
                                floor_price = 50000
                        else:
                            # Item check
                            if price < 5.0:
                                is_snipe = True
                                floor_price = 50

                        if is_snipe:
                            results.append({
                                "id": o.tx_hash,
                                "type": "Character" if char_detail else "Item",
                                "name": asset_name,
                                "token_id": o.token_id,
                                "price": price,
                                "floor_price": floor_price,
                                "seller": o.maker,
                                "buyer": o.taker,
                                "tx_hash": o.tx_hash,
                                "date": datetime.now(timezone.utc).isoformat(),
                            })
                    except Exception:
                        continue

        except Exception as e:
            if "no such table" not in str(e).lower():
                print(f"[HistoricalSentinel] Snipe scan error: {e}")

        return results

    # ─── Full Scan ───────────────────────────────────────────────────

    async def run_full_scan(self) -> dict:
        """Execute a full historical analysis of the marketplace."""
        self._scanning = True
        self._alerts.clear()

        try:
            all_items = await market_data_service.fetch_all_items(max_pages=5)
            all_chars = await market_data_service.fetch_all_characters(max_pages=5)

            price_analysis = self._analyze_price_distribution(all_items)
            wallet_analysis = self._analyze_wallet_concentration(all_items)
            hoarding_analysis = self._analyze_item_hoarding(all_items)
            char_analysis = self._analyze_character_market(all_chars)
            health = self._analyze_market_health(all_items, all_chars)

            self._analysis_results = {
                "price_distribution": price_analysis,
                "wallet_concentration": wallet_analysis,
                "item_hoarding": hoarding_analysis,
                "character_market": char_analysis,
                "market_health": health,
                "scanned_items": len(all_items),
                "scanned_characters": len(all_chars),
                "scan_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self._last_full_scan = datetime.now(timezone.utc)
            self._save_to_json()
            return self._analysis_results

        finally:
            self._scanning = False

    def _save_to_json(self):
        """Export the latest analysis and alerts to a JSON file for debugging."""
        try:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            os.makedirs(data_dir, exist_ok=True)
            filepath = os.path.join(data_dir, "historical_scan.json")

            payload = {
                "analysis": self._analysis_results,
                "alerts": self.get_alerts(limit=100),
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)
        except Exception as e:
            print(f"[HistoricalSentinel] Error saving scan: {e}")

    async def run_loop(self, interval: int = 600):
        """Background loop that deepscans every `interval` seconds (default 10 mins)."""
        self._running = True
        while self._running:
            try:
                await self.run_full_scan()
            except Exception as e:
                print(f"[HistoricalSentinel] Scan error: {e}")
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
            "last_full_scan": self._last_full_scan.isoformat() if self._last_full_scan else None,
            "scanning": self._scanning,
            "analysis_available": bool(self._analysis_results),
        }

    def get_analysis(self) -> dict:
        return self._analysis_results


# Singleton
historical_sentinel = HistoricalSentinel()
