import Redis from "ioredis";
import { config } from "../config";

let client: Redis | null = null;

export function getRedis(): Redis {
  if (!client) {
    client = new Redis(config.redis.url, {
      maxRetriesPerRequest: 3,
      retryStrategy(times) {
        return Math.min(times * 200, 3000);
      },
    });

    client.on("error", (err) => {
      console.error("[Redis] Connection error:", err.message);
    });

    client.on("connect", () => {
      console.log("[Redis] Connected");
    });
  }
  return client;
}

export async function cacheSet(
  key: string,
  value: object,
  ttlSeconds: number = 30
): Promise<void> {
  const redis = getRedis();
  await redis.setex(key, ttlSeconds, JSON.stringify(value));
}

export async function cacheGet<T = any>(key: string): Promise<T | null> {
  const redis = getRedis();
  const data = await redis.get(key);
  return data ? JSON.parse(data) : null;
}

export async function getLastIndexedBlock(): Promise<number> {
  const redis = getRedis();
  const block = await redis.get("indexer:last_block");
  return block ? parseInt(block) : config.indexer.startBlock;
}

export async function setLastIndexedBlock(block: number): Promise<void> {
  const redis = getRedis();
  await redis.set("indexer:last_block", block.toString());
}

export async function publishEvent(
  channel: string,
  data: object
): Promise<void> {
  const redis = getRedis();
  await redis.publish(channel, JSON.stringify(data));
}
