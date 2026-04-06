import { ethers, Log } from "ethers";
import Database from "better-sqlite3";
import { config } from "../config";
import { publishEvent } from "../cache/redis";

const db = new Database(config.dbPath);

// Ensure tables exist
db.exec(`
  CREATE TABLE IF NOT EXISTS nft_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_hash TEXT NOT NULL,
    block_number INTEGER NOT NULL,
    log_index INTEGER NOT NULL,
    contract_address TEXT NOT NULL,
    from_address TEXT NOT NULL,
    to_address TEXT NOT NULL,
    token_id TEXT NOT NULL,
    nft_type TEXT NOT NULL,
    timestamp INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(tx_hash, log_index)
  );
  CREATE INDEX IF NOT EXISTS ix_transfer_token ON nft_transfers(token_id);
  CREATE INDEX IF NOT EXISTS ix_transfer_from ON nft_transfers(from_address);
  CREATE INDEX IF NOT EXISTS ix_transfer_to ON nft_transfers(to_address);
  CREATE INDEX IF NOT EXISTS ix_transfer_block ON nft_transfers(block_number);
`);

const insertStmt = db.prepare(`
  INSERT OR IGNORE INTO nft_transfers
    (tx_hash, block_number, log_index, contract_address, from_address, to_address, token_id, nft_type, timestamp)
  VALUES
    (@txHash, @blockNumber, @logIndex, @contractAddress, @fromAddress, @toAddress, @tokenId, @nftType, @timestamp)
`);

export interface TransferEvent {
  txHash: string;
  blockNumber: number;
  logIndex: number;
  contractAddress: string;
  fromAddress: string;
  toAddress: string;
  tokenId: string;
  nftType: "character" | "item";
  timestamp: number;
}

export function parseTransferLog(
  log: Log,
  nftType: "character" | "item",
  blockTimestamp: number
): TransferEvent | null {
  try {
    const iface = new ethers.Interface([
      "event Transfer(address indexed from, address indexed to, uint256 indexed tokenId)",
    ]);
    const parsed = iface.parseLog({ topics: log.topics as string[], data: log.data });
    if (!parsed) return null;

    return {
      txHash: log.transactionHash,
      blockNumber: log.blockNumber,
      logIndex: log.index,
      contractAddress: log.address.toLowerCase(),
      fromAddress: parsed.args[0].toLowerCase(),
      toAddress: parsed.args[1].toLowerCase(),
      tokenId: parsed.args[2].toString(),
      nftType,
      timestamp: blockTimestamp,
    };
  } catch {
    return null;
  }
}

export async function handleTransfer(event: TransferEvent): Promise<void> {
  // Persist to database
  insertStmt.run({
    txHash: event.txHash,
    blockNumber: event.blockNumber,
    logIndex: event.logIndex,
    contractAddress: event.contractAddress,
    fromAddress: event.fromAddress,
    toAddress: event.toAddress,
    tokenId: event.tokenId,
    nftType: event.nftType,
    timestamp: event.timestamp,
  });

  // Publish real-time event for WebSocket subscribers
  await publishEvent("mapleguard:transfers", {
    type: "transfer",
    nftType: event.nftType,
    tokenId: event.tokenId,
    from: event.fromAddress,
    to: event.toAddress,
    block: event.blockNumber,
    timestamp: event.timestamp,
  });

  // Detect mint (from zero address)
  if (event.fromAddress === "0x0000000000000000000000000000000000000000") {
    await publishEvent("mapleguard:mints", {
      type: "mint",
      nftType: event.nftType,
      tokenId: event.tokenId,
      to: event.toAddress,
      block: event.blockNumber,
    });
  }
}
