import { ethers, Log } from "ethers";
import Database from "better-sqlite3";
import { config } from "../config";
import { publishEvent } from "../cache/redis";

const db = new Database(config.dbPath);

db.exec(`
  CREATE TABLE IF NOT EXISTS order_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_hash TEXT NOT NULL,
    block_number INTEGER NOT NULL,
    log_index INTEGER NOT NULL,
    order_hash TEXT NOT NULL,
    maker TEXT NOT NULL,
    taker TEXT NOT NULL,
    token_id TEXT NOT NULL,
    nft_address TEXT NOT NULL,
    payment_token TEXT NOT NULL,
    price_wei TEXT NOT NULL,
    listing_time INTEGER NOT NULL,
    timestamp INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(tx_hash, log_index)
  );
  CREATE INDEX IF NOT EXISTS ix_order_token ON order_matches(token_id);
  CREATE INDEX IF NOT EXISTS ix_order_maker ON order_matches(maker);
  CREATE INDEX IF NOT EXISTS ix_order_taker ON order_matches(taker);
  CREATE INDEX IF NOT EXISTS ix_order_block ON order_matches(block_number);
  CREATE INDEX IF NOT EXISTS ix_order_nft ON order_matches(nft_address);

  CREATE TABLE IF NOT EXISTS order_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_hash TEXT NOT NULL,
    block_number INTEGER NOT NULL,
    order_hash TEXT NOT NULL,
    maker TEXT NOT NULL,
    token_id TEXT NOT NULL,
    nft_address TEXT NOT NULL,
    payment_token TEXT NOT NULL,
    price_wei TEXT NOT NULL,
    listing_time INTEGER NOT NULL,
    expiration_time INTEGER NOT NULL,
    timestamp INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(order_hash)
  );
  CREATE INDEX IF NOT EXISTS ix_listing_token ON order_listings(token_id);
  CREATE INDEX IF NOT EXISTS ix_listing_block ON order_listings(block_number);
`);

const insertMatchStmt = db.prepare(`
  INSERT OR IGNORE INTO order_matches
    (tx_hash, block_number, log_index, order_hash, maker, taker, token_id, nft_address, payment_token, price_wei, listing_time, timestamp)
  VALUES
    (@txHash, @blockNumber, @logIndex, @orderHash, @maker, @taker, @tokenId, @nftAddress, @paymentToken, @priceWei, @listingTime, @timestamp)
`);

const insertListingStmt = db.prepare(`
  INSERT OR IGNORE INTO order_listings
    (tx_hash, block_number, order_hash, maker, token_id, nft_address, payment_token, price_wei, listing_time, expiration_time, timestamp)
  VALUES
    (@txHash, @blockNumber, @orderHash, @maker, @tokenId, @nftAddress, @paymentToken, @priceWei, @listingTime, @expirationTime, @timestamp)
`);

export interface OrderMatchEvent {
  txHash: string;
  blockNumber: number;
  logIndex: number;
  orderHash: string;
  maker: string;
  taker: string;
  tokenId: string;
  nftAddress: string;
  paymentToken: string;
  priceWei: string;
  listingTime: number;
  timestamp: number;
}

export interface OrderCreatedEvent {
  txHash: string;
  blockNumber: number;
  orderHash: string;
  maker: string;
  tokenId: string;
  nftAddress: string;
  paymentToken: string;
  priceWei: string;
  listingTime: number;
  expirationTime: number;
  timestamp: number;
}

const marketplaceIface = new ethers.Interface([
  "event OrderMatched(bytes32 indexed orderHash, address indexed maker, address indexed taker, uint256 tokenId, address nftAddress, address tokenAddress, uint256 tokenAmount, uint256 listingTime)",
  "event OrderCreated(bytes32 indexed orderHash, address indexed maker, uint256 tokenId, address nftAddress, address tokenAddress, uint256 tokenAmount, uint256 listingTime, uint256 expirationTime)",
]);

export function parseOrderMatchedLog(
  log: Log,
  blockTimestamp: number
): OrderMatchEvent | null {
  try {
    const parsed = marketplaceIface.parseLog({
      topics: log.topics as string[],
      data: log.data,
    });
    if (!parsed || parsed.name !== "OrderMatched") return null;

    return {
      txHash: log.transactionHash,
      blockNumber: log.blockNumber,
      logIndex: log.index,
      orderHash: parsed.args[0],
      maker: parsed.args[1].toLowerCase(),
      taker: parsed.args[2].toLowerCase(),
      tokenId: parsed.args[3].toString(),
      nftAddress: parsed.args[4].toLowerCase(),
      paymentToken: parsed.args[5].toLowerCase(),
      priceWei: parsed.args[6].toString(),
      listingTime: Number(parsed.args[7]),
      timestamp: blockTimestamp,
    };
  } catch {
    return null;
  }
}

export function parseOrderCreatedLog(
  log: Log,
  blockTimestamp: number
): OrderCreatedEvent | null {
  try {
    const parsed = marketplaceIface.parseLog({
      topics: log.topics as string[],
      data: log.data,
    });
    if (!parsed || parsed.name !== "OrderCreated") return null;

    return {
      txHash: log.transactionHash,
      blockNumber: log.blockNumber,
      orderHash: parsed.args[0],
      maker: parsed.args[1].toLowerCase(),
      tokenId: parsed.args[2].toString(),
      nftAddress: parsed.args[3].toLowerCase(),
      paymentToken: parsed.args[4].toLowerCase(),
      priceWei: parsed.args[5].toString(),
      listingTime: Number(parsed.args[6]),
      expirationTime: Number(parsed.args[7]),
      timestamp: blockTimestamp,
    };
  } catch {
    return null;
  }
}

export async function handleOrderMatched(
  event: OrderMatchEvent
): Promise<void> {
  insertMatchStmt.run({
    txHash: event.txHash,
    blockNumber: event.blockNumber,
    logIndex: event.logIndex,
    orderHash: event.orderHash,
    maker: event.maker,
    taker: event.taker,
    tokenId: event.tokenId,
    nftAddress: event.nftAddress,
    paymentToken: event.paymentToken,
    priceWei: event.priceWei,
    listingTime: event.listingTime,
    timestamp: event.timestamp,
  });

  const priceFormatted = (
    Number(BigInt(event.priceWei)) / 1e18
  ).toLocaleString();

  const nftType =
    event.nftAddress === config.contracts.characterNFT.toLowerCase()
      ? "character"
      : "item";

  await publishEvent("mapleguard:sales", {
    type: "sale",
    nftType,
    tokenId: event.tokenId,
    seller: event.maker,
    buyer: event.taker,
    price: priceFormatted,
    priceWei: event.priceWei,
    block: event.blockNumber,
    timestamp: event.timestamp,
  });
}

export async function handleOrderCreated(
  event: OrderCreatedEvent
): Promise<void> {
  insertListingStmt.run({
    txHash: event.txHash,
    blockNumber: event.blockNumber,
    orderHash: event.orderHash,
    maker: event.maker,
    tokenId: event.tokenId,
    nftAddress: event.nftAddress,
    paymentToken: event.paymentToken,
    priceWei: event.priceWei,
    listingTime: event.listingTime,
    expirationTime: event.expirationTime,
    timestamp: event.timestamp,
  });

  await publishEvent("mapleguard:listings", {
    type: "listing",
    tokenId: event.tokenId,
    seller: event.maker,
    priceWei: event.priceWei,
    listingBlock: event.blockNumber,
    listingTime: event.listingTime,
  });
}
