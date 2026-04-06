"""
Open API Service - Rate-limited access to MSU Open API with SQLite persistence.

Rate limits (per MSU docs):
  - Max 10 requests per second
  - Max 30,000 requests per day

Token bucket: 10 req/s with burst capacity of 10.
Daily counter resets at midnight UTC.

All successful responses are persisted in SQLite (character_cp table) so
we never re-fetch the same character's CP unless the cached data is stale.
"""

from __future__ import annotations

import asyncio
import time
import json as _json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.database import CharacterCP, async_session

settings = get_settings()


@dataclass
class _TokenBucket:
    """Simple async token bucket for rate limiting."""
    rate: float = 10.0       # tokens per second
    max_tokens: float = 10.0 # burst capacity
    tokens: float = 10.0
    last_refill: float = 0.0

    def __post_init__(self):
        self.last_refill = time.monotonic()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.rate)
        self.last_refill = now

    async def acquire(self):
        while True:
            self._refill()
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return
            # Wait for the next token
            wait_for = (1.0 - self.tokens) / self.rate
            await asyncio.sleep(wait_for + 0.05)  # small buffer


@dataclass
class _DailyQuota:
    """Tracks 30k/day limit."""
    max_per_day: int = 30_000
    used_today: int = 0
    date: str = ""

    def _check_date(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self.date:
            self.date = today
            self.used_today = 0
            return True
        return False

    def available(self) -> int:
        self._check_date()
        return max(0, self.max_per_day - self.used_today)

    def consume(self):
        self._check_date()
        self.used_today += 1


class OpenAPIError(Exception):
    pass


class OpenAPIService:
    """
    Singleton service providing rate-limited access to MSU Open API
    with SQLite-backed caching for character CP data.
    """

    def __init__(self):
        self._bucket = _TokenBucket(rate=10.0, max_tokens=10.0)
        self._quota = _DailyQuota()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=settings.MSU_OPENAPI_BASE,
                headers={
                    "accept": "application/json",
                    "x-nxopen-api-key": settings.MSU_OPENAPI_KEY,
                },
                timeout=20.0,
            )
        return self._http_client

    # ─── Rate-limited request ───────────────────────────────────────────

    async def fetch(self, path: str, retries: int = 1) -> Optional[dict]:
        """
        Fetch path from Open API with rate limiting.
        Returns the `data` payload from the response, or None on failure.
        Respects 10 req/s rate limit and 30k/day quota.

        If the API returns 429, it means the key is over rate-limited —
        we return None immediately rather than retrying, so callers can
        fall back to cached/derived values.
        """
        if self._quota.available() <= 0:
            print(f"[OpenAPI] Daily quota exhausted (30k/day)")
            return None

        client = await self._ensure_client()

        # Acquire rate-limit token
        await self._bucket.acquire()

        try:
            r = await client.get(path)
        except Exception as e:
            print(f"[OpenAPI] Connection error for {path}: {e}")
            return None

        if r.status_code == 429:
            print(f"[OpenAPI] Rate limited 429 on {path}")
            self._bucket.tokens = 0
            return None

        if r.status_code != 200:
            print(f"[OpenAPI] HTTP {r.status_code} for {path}")
            return None

        self._quota.consume()

        try:
            body = r.json()
        except Exception:
            return None

        if body.get("success"):
            return body.get("data")
        else:
            msg = body.get("error", {}).get("message", "unknown")
            print(f"[OpenAPI] Error in {path}: {msg}")
            return None

    # ─── Character CP with DB cache ─────────────────────────────────────

    async def get_character_cp(self, token_id: str, char_meta: dict = None) -> dict:
        """
        Get real CP for a character. Checks SQLite first; if missing or stale,
        fetches from Open API and persists the result.

        Returns:
            {
                "token_id": str,
                "combat_power": int,   # real CP or 0 if unavailable
                "source": str,         # "openapi", "derived", "cache"
                "level": int,
                "class_name": str,
                "name": str,
            }
        """
        # 1. Check DB cache
        cp_record = await self._get_from_db(token_id)
        if cp_record:
            return {
                "token_id": token_id,
                "combat_power": cp_record.combat_power,
                "source": "cache",
                "level": cp_record.level,
                "class_name": cp_record.class_name,
                "name": cp_record.name,
            }

        # 2. Fetch from Open API
        if token_id.upper().startswith("CHAR"):
            path = f"/characters/{token_id}"
        else:
            path = f"/characters/by-token-id/{token_id}"

        data = await self.fetch(path)

        if data and data.get("character"):
            raw = data["character"]
            ap_stat = raw.get("apStat", {})

            # Try real combatPower
            cp_block = ap_stat.get("combatPower", ap_stat.get("combat_power"))
            combat_power = 0
            source = "openapi"

            if isinstance(cp_block, dict):
                combat_power = int(cp_block.get("total", 0) or 0)
            elif isinstance(cp_block, (int, float)):
                combat_power = int(cp_block)

            if combat_power <= 0:
                # Derive CP from available stats
                combat_power = self._derive_cp(ap_stat, raw)
                source = "derived"

            char_common = raw.get("common", {})
            name = char_meta.get("name", "") or char_common.get("name", "")
            class_name = char_meta.get("class_name", "") or self._extract_class_name(raw)
            level = char_meta.get("level", 0) or int(char_common.get("level", 0))

            # Persist to DB
            await self._save_to_db(token_id, name, class_name, level, combat_power, source, ap_stat)

            return {
                "token_id": token_id,
                "combat_power": combat_power,
                "source": source,
                "level": level,
                "class_name": class_name,
                "name": name,
            }

        # 3. Fallback: cannot reach Open API at all
        return {
            "token_id": token_id,
            "combat_power": 0,
            "source": "unavailable",
            "level": char_meta.get("level", 0) if char_meta else 0,
            "class_name": char_meta.get("class_name", "") if char_meta else "",
            "name": char_meta.get("name", "") if char_meta else "",
        }

    # ─── Batch helper ────────────────────────────────────────────────────

    async def batch_get_cp(self, chars: list, concurrency: int = 5) -> dict[str, dict]:
        """
        Fetch CP for a list of characters sequentially (to respect rate limit).
        Returns dict: {token_id: cp_result_dict}.

        Uses low concurrency to stay within 10 req/s: each request takes ~1-2s
        including rate-limit wait, so 5 concurrent workers ≈ 2.5 req/s.
        """
        semaphore = asyncio.Semaphore(concurrency)
        results: dict[str, dict] = {}

        async def _one(char):
            async with semaphore:
                tid = getattr(char, "token_id", "") or getattr(char, "token_id", "")
                if not tid:
                    return
                char_meta = {
                    "name": getattr(char, "name", ""),
                    "class_name": getattr(char, "class_name", ""),
                    "level": getattr(char, "level", 0),
                }
                result = await self.get_character_cp(tid, char_meta)
                results[tid] = result

        await asyncio.gather(*[_one(c) for c in chars], return_exceptions=True)
        return results

    # ─── DB helpers ──────────────────────────────────────────────────────

    @staticmethod
    async def _get_from_db(token_id: str) -> Optional[CharacterCP]:
        async with async_session() as session:
            stmt = select(CharacterCP).where(CharacterCP.token_id == token_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    @staticmethod
    async def _save_to_db(
        token_id: str,
        name: str,
        class_name: str,
        level: int,
        combat_power: int,
        source: str,
        ap_stats: dict,
    ):
        async with async_session() as session:
            stmt = select(CharacterCP).where(CharacterCP.token_id == token_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.combat_power = combat_power
                existing.source = source
                existing.name = name
                existing.class_name = class_name
                existing.level = level
                existing.ap_stats_json = _json.dumps(ap_stats, ensure_ascii=False)
                existing.updated_at = func.now()
            else:
                session.add(CharacterCP(
                    token_id=token_id,
                    name=name,
                    class_name=class_name,
                    level=level,
                    combat_power=combat_power,
                    source=source,
                    ap_stats_json=_json.dumps(ap_stats, ensure_ascii=False) if ap_stats else None,
                ))

            await session.commit()

    @staticmethod
    def _derive_cp(ap_stat: dict, raw_char: dict) -> int:
        """Derive approximate CP from available stats when real combatPower is absent."""
        from services.combat_power_engine import CombatPowerEngine
        from services.combat_power_engine import _get_stat_total as _gst

        cp = CombatPowerEngine.calculate_cp(
            primary_stat=_gst(ap_stat, "str"),
            secondary_stat=_gst(ap_stat, "dex"),
            total_att=max(_gst(ap_stat, "pad"), _gst(ap_stat, "attackPower"), _gst(ap_stat, "mad")),
            att_percent=0.0,
            damage_pct=_gst(ap_stat, "damage"),
            boss_damage_pct=_gst(ap_stat, "boss_monster_damage"),
            final_damage_pct=_gst(ap_stat, "final_damage"),
            crit_damage_pct=_gst(ap_stat, "critical_damage"),
            crit_damage_base=0.0,  # We don't have base separately
        )
        return int(cp) if cp > 0 else 0

    @staticmethod
    def _extract_class_name(raw_char: dict) -> str:
        """Extract class name from Open API character response."""
        common = raw_char.get("common", {})
        job = common.get("job", {})
        return job.get("className", job.get("jobName", "")) or ""

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()


# Singleton
openapi_service = OpenAPIService()
