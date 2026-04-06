import { ethers } from "ethers";
import { config } from "./config";
import {
  ERC721_TRANSFER_ABI,
  MARKETPLACE_ABI,
} from "./contracts/abis";
import {
  parseTransferLog,
  handleTransfer,
} from "./handlers/transfer";
import {
  parseOrderMatchedLog,
  parseOrderCreatedLog,
  handleOrderMatched,
  handleOrderCreated,
} from "./handlers/order";
import {
  getLastIndexedBlock,
  setLastIndexedBlock,
  getRedis,
} from "./cache/redis";

const provider = new ethers.JsonRpcProvider(config.chain.rpcUrl, {
  chainId: config.chain.chainId,
  name: "henesys",
});

// Topic hashes for the events we monitor
const TRANSFER_TOPIC = ethers.id("Transfer(address,address,uint256)");
const ORDER_MATCHED_TOPIC = ethers.id(
  "OrderMatched(bytes32,address,address,uint256,address,address,uint256,uint256)"
);
const ORDER_CREATED_TOPIC = ethers.id(
  "OrderCreated(bytes32,address,uint256,address,address,uint256,uint256,uint256)"
);

async function processBlockRange(
  fromBlock: number,
  toBlock: number
): Promise<number> {
  let eventsProcessed = 0;

  // Fetch NFT Transfer events (Character + Item contracts)
  const transferFilter = {
    address: [config.contracts.characterNFT, config.contracts.itemNFT],
    topics: [TRANSFER_TOPIC],
    fromBlock,
    toBlock,
  };

  // Fetch Marketplace events
  const marketplaceFilter = {
    address: config.contracts.marketplace,
    topics: [[ORDER_MATCHED_TOPIC, ORDER_CREATED_TOPIC]],
    fromBlock,
    toBlock,
  };

  const [transferLogs, marketplaceLogs] = await Promise.all([
    provider.getLogs(transferFilter),
    provider.getLogs(marketplaceFilter),
  ]);

  // Cache block timestamps to avoid redundant calls
  const blockTimestamps: Map<number, number> = new Map();
  async function getBlockTimestamp(blockNum: number): Promise<number> {
    if (blockTimestamps.has(blockNum)) return blockTimestamps.get(blockNum)!;
    const block = await provider.getBlock(blockNum);
    const ts = block?.timestamp ?? Math.floor(Date.now() / 1000);
    blockTimestamps.set(blockNum, ts);
    return ts;
  }

  // Process NFT transfers
  for (const log of transferLogs) {
    const timestamp = await getBlockTimestamp(log.blockNumber);
    const nftType =
      log.address.toLowerCase() ===
      config.contracts.characterNFT.toLowerCase()
        ? "character"
        : "item";

    const event = parseTransferLog(log as any, nftType, timestamp);
    if (event) {
      await handleTransfer(event);
      eventsProcessed++;
    }
  }

  // Process marketplace events
  for (const log of marketplaceLogs) {
    const timestamp = await getBlockTimestamp(log.blockNumber);

    if (log.topics[0] === ORDER_MATCHED_TOPIC) {
      const event = parseOrderMatchedLog(log as any, timestamp);
      if (event) {
        await handleOrderMatched(event);
        eventsProcessed++;
      }
    } else if (log.topics[0] === ORDER_CREATED_TOPIC) {
      const event = parseOrderCreatedLog(log as any, timestamp);
      if (event) {
        await handleOrderCreated(event);
        eventsProcessed++;
      }
    }
  }

  return eventsProcessed;
}

async function runIndexer(): Promise<void> {
  console.log("========================================");
  console.log("  MapleGuard Blockchain Indexer v1.0");
  console.log("  Chain: Henesys (ID: 68414)");
  console.log("========================================");
  console.log(`  RPC: ${config.chain.rpcUrl}`);
  console.log(`  Marketplace: ${config.contracts.marketplace}`);
  console.log(`  Character NFT: ${config.contracts.characterNFT}`);
  console.log(`  Item NFT: ${config.contracts.itemNFT}`);
  console.log("========================================\n");

  let lastBlock = await getLastIndexedBlock();
  const currentBlock = await provider.getBlockNumber();

  if (lastBlock === 0) {
    // Start from recent blocks if no checkpoint
    lastBlock = Math.max(0, currentBlock - 1000);
    console.log(
      `[Indexer] No checkpoint found, starting from block ${lastBlock}`
    );
  } else {
    console.log(`[Indexer] Resuming from block ${lastBlock}`);
  }

  console.log(`[Indexer] Current chain head: ${currentBlock}\n`);

  // Catch-up phase: process historical blocks in batches
  while (lastBlock < currentBlock) {
    const fromBlock = lastBlock + 1;
    const toBlock = Math.min(
      fromBlock + config.indexer.batchSize - 1,
      currentBlock
    );

    try {
      const count = await processBlockRange(fromBlock, toBlock);
      await setLastIndexedBlock(toBlock);
      lastBlock = toBlock;

      if (count > 0) {
        console.log(
          `[Indexer] Blocks ${fromBlock}-${toBlock}: ${count} events indexed`
        );
      }
    } catch (err: any) {
      console.error(
        `[Indexer] Error processing blocks ${fromBlock}-${toBlock}:`,
        err.message
      );
      // Wait before retry
      await new Promise((r) => setTimeout(r, 5000));
    }
  }

  console.log("[Indexer] Catch-up complete. Switching to live mode...\n");

  // Live mode: poll for new blocks
  while (true) {
    try {
      const headBlock = await provider.getBlockNumber();

      if (headBlock > lastBlock) {
        const fromBlock = lastBlock + 1;
        const count = await processBlockRange(fromBlock, headBlock);
        await setLastIndexedBlock(headBlock);
        lastBlock = headBlock;

        if (count > 0) {
          console.log(
            `[Indexer] Block ${headBlock}: ${count} events indexed`
          );
        }
      }
    } catch (err: any) {
      console.error("[Indexer] Poll error:", err.message);
    }

    await new Promise((r) => setTimeout(r, config.indexer.pollInterval));
  }
}

// Graceful shutdown
process.on("SIGINT", async () => {
  console.log("\n[Indexer] Shutting down...");
  const redis = getRedis();
  redis.disconnect();
  process.exit(0);
});

runIndexer().catch((err) => {
  console.error("[Indexer] Fatal error:", err);
  process.exit(1);
});
