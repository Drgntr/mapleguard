"""
Leaderboard DB Service — reads all leaderboard data from SQLite.

Endpoints query pre-computed CP and snapshots instead of calling
external APIs, making responses instant (<100ms).
"""

import json
from typing import Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import (
    async_session, CharacterSnapshot, ItemSnapshot,
    MintEvent, NftMintLookup, SyncState,
)


class LeaderboardDBService:

    # ── Helpers ──────────────────────────────────────────────────────

    async def _get_session(self) -> AsyncSession:
        return async_session()

    async def _sync_state_get(self, key: str, default: str = "") -> str:
        async with self._get_session() as session:
            row = await session.execute(select(SyncState).where(SyncState.key == key))
            s = row.scalar_one_or_none()
            return s.value if s else default

    # ── Character Leaderboard ────────────────────────────────────────

    async def get_cp_leaderboard(
        self, class_name: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> dict:
        """Top CP characters, optionally filtered by class."""
        async with self._get_session() as session:
            q = select(CharacterSnapshot).where(CharacterSnapshot.combat_power > 0)
            if class_name and class_name != "all" and class_name != "all_classes":
                q = q.where(CharacterSnapshot.class_name == class_name)
            q = q.order_by(CharacterSnapshot.combat_power.desc())
            q = q.offset(offset).limit(limit)
            rows = (await session.execute(q)).scalars().all()

            # Get total count for pagination
            count_q = select(func.count(CharacterSnapshot.id))\
                .where(CharacterSnapshot.combat_power > 0)
            if class_name and class_name != "all" and class_name != "all_classes":
                count_q = count_q.where(CharacterSnapshot.class_name == class_name)
            total = (await session.execute(count_q)).scalar() or 0

            chars = [
                {
                    "token_id": r.token_id,
                    "name": r.name,
                    "class_name": r.class_name,
                    "level": r.level,
                    "combat_power": r.combat_power,
                    "char_att": r.char_att,
                    "char_matt": r.char_matt,
                    "image_url": r.image_url,
                    "source": r.source,
                }
                for r in rows
            ]

            return {
                "class_name": class_name or "all",
                "characters": chars,
                "total": total,
            }

    async def get_combined_leaderboard(self, limit: int = 100, offset: int = 0) -> dict:
        """Top CP characters across all classes with class grouping."""
        async with self._get_session() as session:
            q = select(CharacterSnapshot).where(CharacterSnapshot.combat_power > 0)\
                .order_by(CharacterSnapshot.combat_power.desc())\
                .offset(offset).limit(limit)
            rows = (await session.execute(q)).scalars().all()

            all_q = select(func.count(CharacterSnapshot.id)).where(CharacterSnapshot.combat_power > 0)
            total = (await session.execute(all_q)).scalar() or 0

            groups = {}
            chars = []
            for r in rows:
                entry = {
                    "token_id": r.token_id,
                    "name": r.name,
                    "class_name": r.class_name,
                    "level": r.level,
                    "combat_power": r.combat_power,
                    "image_url": r.image_url,
                }
                chars.append(entry)
                cls = r.class_name or "Unknown"
                groups.setdefault(cls, []).append(entry)

            return {
                "top_characters": chars,
                "total_scored": total,
                "classes": groups,
            }

    # ── Detail Lookups ───────────────────────────────────────────────

    async def get_char_detail(self, token_id: str) -> Optional[dict]:
        """Full character snapshot detail."""
        async with self._get_session() as session:
            q = select(CharacterSnapshot).where(CharacterSnapshot.token_id == token_id)
            row = (await session.execute(q)).scalar_one_or_none()
            if not row:
                return None
            return {
                "token_id": row.token_id,
                "asset_key": row.asset_key,
                "name": row.name,
                "class_name": row.class_name,
                "job_name": row.job_name,
                "class_code": row.class_code,
                "job_code": row.job_code,
                "level": row.level,
                "combat_power": row.combat_power,
                "char_att": row.char_att,
                "char_matt": row.char_matt,
                "ap_stats": json.loads(row.ap_stats_json) if row.ap_stats_json else None,
                "hyper_stats": json.loads(row.hyper_stats_json) if row.hyper_stats_json else None,
                "wearing": json.loads(row.wearing_json) if row.wearing_json else None,
                "equipped_items": json.loads(row.equipped_items_json) if row.equipped_items_json else None,
                "image_url": row.image_url,
                "price_wei": row.price_wei,
                "source": row.source,
                "last_synced": str(row.last_synced),
            }

    async def get_item_detail(self, token_id: str) -> Optional[dict]:
        """Full item snapshot detail."""
        async with self._get_session() as session:
            q = select(ItemSnapshot).where(ItemSnapshot.token_id == token_id)
            row = (await session.execute(q)).scalar_one_or_none()
            if not row:
                return None
            return {
                "token_id": row.token_id,
                "asset_key": row.asset_key,
                "name": row.name,
                "category_no": row.category_no,
                "category_label": row.category_label,
                "item_id": row.item_id,
                "starforce": row.starforce,
                "enable_starforce": row.enable_starforce,
                "potential_grade": row.potential_grade,
                "bonus_potential_grade": row.bonus_potential_grade,
                "stats": json.loads(row.stats_json) if row.stats_json else None,
                "potential": json.loads(row.potential_json) if row.potential_json else None,
                "bonus_potential": json.loads(row.bonus_potential_json) if row.bonus_potential_json else None,
                "attributes": json.loads(row.attributes_json) if row.attributes_json else None,
                "image_url": row.image_url,
                "price_wei": row.price_wei,
                "source": row.source,
                "last_synced": str(row.last_synced),
            }

    # ── Mint Events ──────────────────────────────────────────────────

    async def get_recent_mints(self, nft_type: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Recent mint events."""
        async with self._get_session() as session:
            q = select(MintEvent)
            if nft_type:
                q = q.where(MintEvent.nft_type == nft_type)
            q = q.order_by(MintEvent.id.desc()).limit(limit)
            rows = (await session.execute(q)).scalars().all()
            return [
                {
                    "token_id": r.token_id,
                    "nft_type": r.nft_type,
                    "minter": r.minter,
                    "block_number": r.block_number,
                    "enriched": r.enriched,
                    "created_at": str(r.created_at),
                }
                for r in rows
            ]

    # ── Stats ────────────────────────────────────────────────────────

    async def get_stats(self) -> dict:
        """Dashboard-style stats."""
        try:
            async with self._get_session() as session:
                char_count = (await session.execute(
                    select(func.count(CharacterSnapshot.id))
                )).scalar() or 0
                item_count = (await session.execute(
                    select(func.count(ItemSnapshot.id))
                )).scalar() or 0
                mint_lookup_count = (await session.execute(
                    select(func.count(NftMintLookup.id))
                )).scalar() or 0
                pending_chars = mint_lookup_count - char_count if mint_lookup_count > 0 else 0

                last_char_block = await self._sync_state_get("scan_characters_last_block", "0")
                last_item_block = await self._sync_state_get("scan_items_last_block", "0")
                enrich_char_at = await self._sync_state_get("enrich_characters_last_token", "")
                enrich_item_at = await self._sync_state_get("enrich_items_last_token", "")

                # Class distribution
                class_q = select(CharacterSnapshot.class_name, func.count(CharacterSnapshot.id)).group_by(CharacterSnapshot.class_name)
                class_rows = (await session.execute(class_q)).all()
                class_distribution = {row[0]: row[1] for row in class_rows}

                # Item category distribution
                cat_q = select(ItemSnapshot.category_label, func.count(ItemSnapshot.id)).group_by(ItemSnapshot.category_label)
                cat_rows = (await session.execute(cat_q)).all()
                category_distribution = {row[0]: row[1] for row in cat_rows}

                # Unenriched mint events
                unenriched_mints = (await session.execute(
                    select(func.count(MintEvent.id)).where(MintEvent.enriched == False)
                )).scalar() or 0

                return {
                    "characters": {
                        "total_minted": mint_lookup_count,
                        "enriched": char_count,
                        "pending_enrichment": max(pending_chars, 0),
                        "last_scanned_block": int(last_char_block) if last_char_block.isdigit() else 0,
                    },
                    "items": {
                        "total_minted": mint_lookup_count,
                        "enriched": item_count,
                        "last_scanned_block": int(last_item_block) if last_item_block.isdigit() else 0,
                    },
                    "class_distribution": dict(sorted(class_distribution.items(), key=lambda x: x[1], reverse=True)[:30]),
                    "category_distribution": dict(sorted(category_distribution.items(), key=lambda x: x[1], reverse=True)[:30]),
                    "unenriched_mints": unenriched_mints,
                    "enrichment_state": {
                        "last_char_token": enrich_char_at,
                        "last_item_token": enrich_item_at,
                    },
                }
        except Exception as e:
            import traceback
            print(f"[Stats ERROR] {e}")
            traceback.print_exc()
            return {
                "characters": {"total_minted": 0, "enriched": 0, "pending_enrichment": 0, "last_scanned_block": 0},
                "items": {"total_minted": 0, "enriched": 0, "last_scanned_block": 0},
                "class_distribution": {},
                "category_distribution": {},
                "unenriched_mints": 0,
                "enrichment_state": {},
                "error": str(e),
            }

    async def get_classes(self) -> list[dict]:
        """List all known classes with character counts and max CP."""
        async with self._get_session() as session:
            sub = select(
                CharacterSnapshot.class_name,
                func.count(CharacterSnapshot.id).label("count"),
                func.max(CharacterSnapshot.combat_power).label("max_cp"),
            ).where(CharacterSnapshot.class_name != "")\
             .group_by(CharacterSnapshot.class_name)\
             .order_by(func.count(CharacterSnapshot.id).desc())
            rows = (await session.execute(sub)).all()
            return [
                {
                    "class_name": r[0],
                    "count": r[1],
                    "max_cp": r[2] or 0,
                }
                for r in rows
            ]

    async def search_characters(self, query: str, limit: int = 20) -> list[dict]:
        """Search characters by name or class."""
        async with self._get_session() as session:
            q = select(CharacterSnapshot).where(
                or_(
                    CharacterSnapshot.name.ilike(f"%{query}%"),
                    CharacterSnapshot.class_name.ilike(f"%{query}%"),
                    CharacterSnapshot.job_name.ilike(f"%{query}%"),
                )
            ).order_by(CharacterSnapshot.combat_power.desc()).limit(limit)
            rows = (await session.execute(q)).scalars().all()
            return [
                {
                    "token_id": r.token_id,
                    "name": r.name,
                    "class_name": r.class_name,
                    "level": r.level,
                    "combat_power": r.combat_power,
                    "image_url": r.image_url,
                }
                for r in rows
            ]

    async def mark_char_enriched(self, token_id: str):
        """Mark character enrichment as last processed."""
        async with self._get_session() as session:
            row = await session.execute(select(SyncState).where(SyncState.key == "enrich_characters_last_token"))
            s = row.scalar_one_or_none()
            if s:
                s.value = token_id
            else:
                session.add(SyncState(key="enrich_characters_last_token", value=token_id))
            await session.commit()

    async def mark_item_enriched(self, token_id: str):
        """Mark item enrichment as last processed."""
        async with self._get_session() as session:
            row = await session.execute(select(SyncState).where(SyncState.key == "enrich_items_last_token"))
            s = row.scalar_one_or_none()
            if s:
                s.value = token_id
            else:
                session.add(SyncState(key="enrich_items_last_token", value=token_id))
            await session.commit()

    async def save_sync_state(self, key: str, value: str):
        """Save arbitrary sync state."""
        async with self._get_session() as session:
            row = await session.execute(select(SyncState).where(SyncState.key == key))
            s = row.scalar_one_or_none()
            if s:
                s.value = value
            else:
                session.add(SyncState(key=key, value=value))
            await session.commit()

    # ── Job Leaderboard ────────────────────────────────────────────────

    async def get_job_leaderboard(
        self, job_name: Optional[str] = None, limit: int = 100
    ) -> dict:
        """Top CP characters by job. Returns top 10 highlighted + full list."""
        async with self._get_session() as session:
            base_q = select(CharacterSnapshot).where(
                CharacterSnapshot.combat_power > 0
            )
            if job_name:
                base_q = base_q.where(CharacterSnapshot.job_name == job_name)

            # Total count
            count_q = select(func.count(CharacterSnapshot.id)).where(
                CharacterSnapshot.combat_power > 0
            )
            if job_name:
                count_q = count_q.where(CharacterSnapshot.job_name == job_name)
            total = (await session.execute(count_q)).scalar() or 0

            # Full list ordered by CP
            rows = (
                await session.execute(
                    base_q.order_by(CharacterSnapshot.combat_power.desc()).limit(limit)
                )
            ).scalars().all()

            chars = [
                {
                    "token_id": r.token_id,
                    "name": r.name,
                    "class_name": r.class_name,
                    "job_name": r.job_name,
                    "level": r.level,
                    "combat_power": r.combat_power,
                    "char_att": r.char_att,
                    "char_matt": r.char_matt,
                    "image_url": r.image_url,
                    "source": r.source,
                }
                for r in rows
            ]

            return {
                "job_name": job_name or "all",
                "top10": chars[:10],
                "all": chars,
                "total": total,
            }

    async def list_jobs(self) -> list[dict]:
        """List all known jobs with character counts and max CP."""
        async with self._get_session() as session:
            rows = (
                await session.execute(
                    select(
                        CharacterSnapshot.job_name,
                        func.count(CharacterSnapshot.id).label("count"),
                        func.max(CharacterSnapshot.combat_power).label("max_cp"),
                        func.max(CharacterSnapshot.class_name).label("class_name"),
                    )
                    .where(CharacterSnapshot.job_name != "")
                    .group_by(CharacterSnapshot.job_name)
                    .order_by(func.count(CharacterSnapshot.id).desc())
                )
            ).all()

            return [
                {
                    "job_name": r[0],
                    "count": r[1],
                    "max_cp": r[2] or 0,
                    "class_name": r[3] or "",
                }
                for r in rows
            ]


leaderboard_db_service = LeaderboardDBService()
