"""
Anomaly Detection Engine for MapleStory Universe marketplace.

Detects:
1. Wash Trading - repeated transactions between same wallets in short windows
2. Bot Sniping - purchases in the same block as listing (bypassing 30s rule)
3. Price Manipulation - artificial price inflation/deflation patterns
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib

from models.item import ItemListing
from models.market import AnomalyAlert, AnomalyType
from config import get_settings

settings = get_settings()


class AnomalyDetector:
    """
    Stateful detector that accumulates transactions and runs detection
    algorithms against the rolling window.
    """

    def __init__(self):
        # wallet_pair -> list of (timestamp, token_id, tx_hash, block_number)
        self._pair_history: dict[str, list[dict]] = defaultdict(list)
        # token_id -> (listing_block, listing_timestamp)
        self._listing_info: dict[str, dict] = {}
        # All detected anomalies (deduped by id)
        self._anomalies: dict[str, AnomalyAlert] = {}

    def _make_pair_key(self, wallet_a: str, wallet_b: str) -> str:
        """Canonical key for a wallet pair (order-independent)."""
        pair = sorted([wallet_a.lower(), wallet_b.lower()])
        return f"{pair[0]}:{pair[1]}"

    def _make_alert_id(self, anomaly_type: str, *args) -> str:
        raw = f"{anomaly_type}:{'|'.join(str(a) for a in args)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def register_listing(self, token_id: str, block_number: int, timestamp: datetime):
        """Register when an item was listed (for snipe detection)."""
        self._listing_info[token_id] = {
            "block": block_number,
            "timestamp": timestamp,
        }

    def ingest_transaction(self, tx: dict):
        """
        Ingest a marketplace transaction for analysis.

        Expected tx dict:
        {
            "seller": "0x...",
            "buyer": "0x...",
            "token_id": "...",
            "tx_hash": "0x...",
            "block_number": int,
            "timestamp": datetime,
            "price": float,
            "item_name": str,
        }
        """
        seller = tx.get("seller", "")
        buyer = tx.get("buyer", "")
        if not seller or not buyer:
            return

        # Track pair history for wash trade detection
        pair_key = self._make_pair_key(seller, buyer)
        self._pair_history[pair_key].append({
            "timestamp": tx["timestamp"],
            "token_id": tx["token_id"],
            "tx_hash": tx.get("tx_hash", ""),
            "block_number": tx.get("block_number", 0),
            "price": tx.get("price", 0),
            "item_name": tx.get("item_name", ""),
        })

        # Run detections
        alerts = []
        alerts.extend(self._detect_wash_trade(pair_key, seller, buyer))
        alerts.extend(self._detect_same_block_snipe(tx))

        for alert in alerts:
            self._anomalies[alert.id] = alert

    def _detect_wash_trade(
        self, pair_key: str, wallet_a: str, wallet_b: str
    ) -> list[AnomalyAlert]:
        """
        Wash Trade Detection:
        If the same wallet pair has >= WASH_TRADE_MIN_TXNS transactions
        within WASH_TRADE_WINDOW_SECONDS, flag as wash trading.
        """
        alerts = []
        history = self._pair_history[pair_key]
        window = timedelta(seconds=settings.WASH_TRADE_WINDOW_SECONDS)
        now = datetime.now(timezone.utc)

        # Filter to recent window
        recent = [h for h in history if now - h["timestamp"] <= window]

        if len(recent) >= settings.WASH_TRADE_MIN_TXNS:
            tokens_involved = list({h["token_id"] for h in recent})
            tx_hashes = [h["tx_hash"] for h in recent if h["tx_hash"]]

            # Severity based on transaction count
            if len(recent) >= 10:
                severity = "critical"
            elif len(recent) >= 6:
                severity = "high"
            elif len(recent) >= 4:
                severity = "medium"
            else:
                severity = "low"

            alert_id = self._make_alert_id("wash_trade", pair_key, len(recent))
            alert = AnomalyAlert(
                id=alert_id,
                anomaly_type=AnomalyType.WASH_TRADE,
                severity=severity,
                description=(
                    f"Wash trading detected: {len(recent)} transactions between "
                    f"{wallet_a[:8]}...{wallet_a[-4:]} and {wallet_b[:8]}...{wallet_b[-4:]} "
                    f"within {settings.WASH_TRADE_WINDOW_SECONDS // 60} minutes. "
                    f"Items: {', '.join(recent[0].get('item_name', t) for t in tokens_involved[:3])}"
                ),
                involved_wallets=[wallet_a, wallet_b],
                involved_tokens=tokens_involved,
                transaction_hashes=tx_hashes,
                detected_at=now,
                block_number=recent[-1].get("block_number"),
                metadata={
                    "transaction_count": len(recent),
                    "window_seconds": settings.WASH_TRADE_WINDOW_SECONDS,
                    "avg_price": sum(h["price"] for h in recent) / len(recent),
                },
            )
            alerts.append(alert)

        return alerts

    def _detect_same_block_snipe(self, tx: dict) -> list[AnomalyAlert]:
        """
        Same-Block Snipe Detection:
        MSU marketplace requires 30s wait after listing before purchase.
        If a buy happens within SNIPE_BLOCK_THRESHOLD blocks of the listing,
        it's likely a bot circumventing the delay.
        """
        alerts = []
        token_id = tx["token_id"]
        buy_block = tx.get("block_number", 0)

        listing = self._listing_info.get(token_id)
        if not listing or buy_block == 0:
            return alerts

        listing_block = listing["block"]
        block_diff = buy_block - listing_block

        if block_diff <= settings.SNIPE_BLOCK_THRESHOLD and block_diff >= 0:
            # Also check timestamp difference
            listing_ts = listing["timestamp"]
            buy_ts = tx["timestamp"]
            time_diff = (buy_ts - listing_ts).total_seconds()

            # Flag if purchase happened < 30s after listing
            if time_diff < 30:
                severity = "critical" if block_diff == 0 else "high"

                alert_id = self._make_alert_id(
                    "same_block_snipe", token_id, buy_block
                )
                alert = AnomalyAlert(
                    id=alert_id,
                    anomaly_type=AnomalyType.SAME_BLOCK_SNIPE,
                    severity=severity,
                    description=(
                        f"Bot snipe detected: {tx.get('item_name', token_id)} purchased "
                        f"{time_diff:.1f}s after listing (block diff: {block_diff}). "
                        f"Buyer: {tx['buyer'][:8]}...{tx['buyer'][-4:]}. "
                        f"30s minimum wait was bypassed."
                    ),
                    involved_wallets=[tx.get("seller", ""), tx["buyer"]],
                    involved_tokens=[token_id],
                    transaction_hashes=[tx.get("tx_hash", "")],
                    detected_at=datetime.now(timezone.utc),
                    block_number=buy_block,
                    metadata={
                        "listing_block": listing_block,
                        "buy_block": buy_block,
                        "block_diff": block_diff,
                        "time_diff_seconds": time_diff,
                        "price": tx.get("price", 0),
                    },
                )
                alerts.append(alert)

        return alerts

    def detect_price_manipulation(
        self, item_name: str, recent_sales: list[dict]
    ) -> Optional[AnomalyAlert]:
        """
        Price Manipulation Detection:
        Identifies artificial inflation by checking if a small set of wallets
        are pushing prices up/down through coordinated trades.
        """
        if len(recent_sales) < 5:
            return None

        # Group by wallet
        wallet_trades: dict[str, list] = defaultdict(list)
        for sale in recent_sales:
            buyer = sale.get("buyer", "")
            if buyer:
                wallet_trades[buyer].append(sale)

        # Check for concentration: if > 60% of trades are by same 2 wallets
        total = len(recent_sales)
        sorted_wallets = sorted(
            wallet_trades.items(), key=lambda x: len(x[1]), reverse=True
        )

        if len(sorted_wallets) >= 2:
            top2_count = sum(len(trades) for _, trades in sorted_wallets[:2])
            concentration = top2_count / total

            if concentration > 0.6:
                wallets = [w for w, _ in sorted_wallets[:2]]
                prices = [s.get("price", 0) for s in recent_sales]
                price_trend = prices[-1] - prices[0] if prices else 0

                alert_id = self._make_alert_id(
                    "price_manipulation", item_name, wallets[0]
                )
                return AnomalyAlert(
                    id=alert_id,
                    anomaly_type=AnomalyType.PRICE_MANIPULATION,
                    severity="high",
                    description=(
                        f"Price manipulation suspected for '{item_name}': "
                        f"{concentration:.0%} of {total} recent trades concentrated in "
                        f"2 wallets. Price {'increased' if price_trend > 0 else 'decreased'} "
                        f"by {abs(price_trend):,.0f} NESO."
                    ),
                    involved_wallets=wallets,
                    involved_tokens=[],
                    transaction_hashes=[
                        s.get("tx_hash", "") for s in recent_sales if s.get("tx_hash")
                    ],
                    detected_at=datetime.now(timezone.utc),
                    metadata={
                        "concentration": round(concentration, 3),
                        "total_trades": total,
                        "price_change": price_trend,
                        "top_wallet_trades": len(sorted_wallets[0][1]),
                    },
                )
        return None

    def get_alerts(
        self,
        severity: Optional[str] = None,
        anomaly_type: Optional[AnomalyType] = None,
        limit: int = 50,
    ) -> list[AnomalyAlert]:
        """Get detected anomalies with optional filtering."""
        alerts = list(self._anomalies.values())

        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if anomaly_type:
            alerts = [a for a in alerts if a.anomaly_type == anomaly_type]

        alerts.sort(key=lambda a: a.detected_at, reverse=True)
        return alerts[:limit]

    def get_stats(self) -> dict:
        """Summary statistics for the anomaly detector."""
        alerts = list(self._anomalies.values())
        return {
            "total_alerts": len(alerts),
            "by_type": {
                t.value: len([a for a in alerts if a.anomaly_type == t])
                for t in AnomalyType
            },
            "by_severity": {
                s: len([a for a in alerts if a.severity == s])
                for s in ["low", "medium", "high", "critical"]
            },
            "tracked_wallet_pairs": len(self._pair_history),
            "tracked_listings": len(self._listing_info),
        }


# Singleton
anomaly_detector = AnomalyDetector()
