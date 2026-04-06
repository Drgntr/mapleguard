import useSWR from "swr";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

const fetcher = (url: string) =>
  fetch(`${API_BASE}${url}`).then((r) => r.json());

export function useMarketOverview() {
  return useSWR("/api/market/overview", fetcher, { refreshInterval: 30000 });
}

export function useItems(page = 1, pageSize = 50, sorting = "ExploreSorting_RECENTLY_LISTED") {
  return useSWR(
    `/api/items/?page=${page}&page_size=${pageSize}&sorting=${sorting}`,
    fetcher,
    { refreshInterval: 15000 }
  );
}

export function useRecentlyListed(count = 30) {
  return useSWR(`/api/items/recently-listed?count=${count}`, fetcher, {
    refreshInterval: 10000,
  });
}

export function useConsumables() {
  return useSWR("/api/items/consumables", fetcher, { refreshInterval: 60000 });
}

export function useUnderpricedItems(threshold = 0.3) {
  return useSWR(
    `/api/items/underpriced?discount_threshold=${threshold}&limit=50`,
    fetcher,
    { refreshInterval: 30000 }
  );
}

export function useAnomalies(limit = 50) {
  return useSWR(`/api/market/anomalies?limit=${limit}`, fetcher, {
    refreshInterval: 20000,
  });
}

export function useCharacters(
  page = 1,
  pageSize = 50,
  classFilter = "all_classes",
  jobFilter = "all_jobs",
  levelMin = 0,
  levelMax = 300
) {
  return useSWR(
    `/api/characters/?page=${page}&page_size=${pageSize}&class_filter=${classFilter}&job_filter=${jobFilter}&level_min=${levelMin}&level_max=${levelMax}`,
    fetcher,
    { refreshInterval: 15000 }
  );
}

export function useFloorPrices() {
  return useSWR("/api/characters/floor-prices", fetcher, {
    refreshInterval: 120000,
  });
}

export function useItemFloorPrices() {
  return useSWR("/api/items/floor-prices", fetcher, {
    refreshInterval: 120000,
  });
}

export function useScarcityRanking(limit = 50) {
  return useSWR(`/api/market/scarcity-ranking?limit=${limit}`, fetcher, {
    refreshInterval: 120000,
  });
}

export function useItemOHLC(itemId: number | null, interval = 60) {
  return useSWR(
    itemId ? `/api/items/ohlc/${itemId}?interval=${interval}` : null,
    fetcher
  );
}

export function useTradeHistory(itemId: number | null) {
  return useSWR(
    itemId ? `/api/items/trade-history/${itemId}` : null,
    fetcher
  );
}

export function useCharacterDetail(tokenId: string | null) {
  return useSWR(
    tokenId ? `/api/characters/${tokenId}/detail` : null,
    fetcher,
    { revalidateOnFocus: true, revalidateOnReconnect: true, dedupingInterval: 5000 }
  );
}

export function useItemDetail(tokenId: string | null) {
  return useSWR(
    tokenId ? `/api/items/${tokenId}/detail` : null,
    fetcher
  );
}

// --- Sentinel API Hooks ---

export function useLiveSentinelStats() {
  return useSWR("/api/market/sentinel/live/stats", fetcher, { refreshInterval: 15000 });
}

export function useLiveSentinelAlerts(limit = 50) {
  return useSWR(`/api/market/sentinel/live/alerts?limit=${limit}`, fetcher, { refreshInterval: 15000 });
}

export function useHistoricalAnalysis() {
  return useSWR("/api/market/sentinel/historical/analysis", fetcher, { refreshInterval: 60000 });
}

export function useHistoricalAlerts(limit = 50) {
  return useSWR(`/api/market/sentinel/historical/alerts?limit=${limit}`, fetcher, { refreshInterval: 60000 });
}

export async function triggerHistoricalScan() {
  return fetch("/api/market/sentinel/historical/scan", { method: "POST" }).then(res => res.json());
}

export function useWhaleLeaderboards() {
  return useSWR("/api/market/whales/leaderboards", fetcher, {
    refreshInterval: 60000,
  });
}

export function useLeaderboardScan(limit = 100) {
  return useSWR(`/api/leaderboard/scan?limit=${limit}`, fetcher, {
    refreshInterval: 0,
    revalidateOnFocus: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useHistoricalSnipes() {
  return useSWR("/api/market/sentinel/snipes", fetcher, {
    refreshInterval: 60000,
  });
}

export function useSniperRanking(limit = 50) {
  return useSWR(`/api/market/sentinel/sniper-ranking?limit=${limit}`, fetcher, {
    refreshInterval: 0,
    revalidateOnFocus: false,
  });
}

export function useStaticSnipes(page = 1, pageSize = 50, filterType = "all") {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    ...(filterType !== "all" ? { filter_type: filterType } : {}),
  });
  return useSWR(`/api/market/sentinel/snipes/static?${params}`, fetcher, {
    refreshInterval: 0,
    revalidateOnFocus: false,
  });
}

// --- Leaderboard DB Hooks ---

export function useLeaderboardStats() {
  return useSWR("/api/leaderboard/stats", fetcher, {
    refreshInterval: 60000,
  });
}

export function useLeaderboardCombined(limit = 100) {
  return useSWR(`/api/leaderboard/combined?limit=${limit}`, fetcher, {
    refreshInterval: 60000,
  });
}

export function useLeaderboardByClass(className?: string, limit = 50) {
  const url = className
    ? `/api/leaderboard/by-class?class_name=${encodeURIComponent(className)}&limit=${limit}`
    : `/api/leaderboard/by-class?limit=${limit}`;
  return useSWR(url, fetcher, {
    refreshInterval: 60000,
  });
}

export function useLeaderboardClasses() {
  return useSWR("/api/leaderboard/classes", fetcher, {
    refreshInterval: 120000,
  });
}

export function useCharacterDetailFromDB(tokenId: string | null) {
  return useSWR(
    tokenId ? `/api/leaderboard/characters/${tokenId}` : null,
    fetcher,
    { revalidateOnFocus: false, dedupingInterval: 30000 }
  );
}

export function useItemDetailFromDB(tokenId: string | null) {
  return useSWR(
    tokenId ? `/api/leaderboard/items/${tokenId}` : null,
    fetcher,
    { revalidateOnFocus: false, dedupingInterval: 30000 }
  );
}

export function useRecentMints(nftType?: string, limit = 50) {
  const url = nftType
    ? `/api/leaderboard/recent-mints?nft_type=${nftType}&limit=${limit}`
    : `/api/leaderboard/recent-mints?limit=${limit}`;
  return useSWR(url, fetcher, {
    refreshInterval: 30000,
  });
}
