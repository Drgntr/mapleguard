const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchAPI<T = any>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Items
export const getItems = (page = 1, pageSize = 50) =>
  fetchAPI(`/api/items/?page=${page}&page_size=${pageSize}`);

export const getRecentlyListed = (count = 30) =>
  fetchAPI(`/api/items/recently-listed?count=${count}`);

export const getItemScarcity = (tokenId: string) =>
  fetchAPI(`/api/items/${tokenId}/scarcity`);

export const getUnderpricedItems = (threshold = 0.3, limit = 50) =>
  fetchAPI(
    `/api/items/underpriced?discount_threshold=${threshold}&limit=${limit}`
  );

export const getItemOHLC = (itemName: string, interval = 60) =>
  fetchAPI(
    `/api/items/${encodeURIComponent(itemName)}/ohlc?interval=${interval}`
  );

// Characters
export const getCharacters = (page = 1, pageSize = 50) =>
  fetchAPI(`/api/characters/?page=${page}&page_size=${pageSize}`);

export const getFloorPrices = () => fetchAPI(`/api/characters/floor-prices`);

// Market
export const getMarketOverview = () => fetchAPI(`/api/market/overview`);

export const getAnomalies = (limit = 50) =>
  fetchAPI(`/api/market/anomalies?limit=${limit}`);

export const getScarcityRanking = (limit = 50) =>
  fetchAPI(`/api/market/scarcity-ranking?limit=${limit}`);
