import dotenv from "dotenv";
dotenv.config({ path: "../.env" });

export const config = {
  // Henesys Chain (MapleStory Universe L2)
  chain: {
    chainId: 68414,
    rpcUrl:
      process.env.RPC_URL ||
      "https://subnets.avax.network/maplestory/mainnet/rpc",
    blockTime: 2, // ~2 second blocks
  },

  // Smart Contract Addresses
  contracts: {
    marketplace: "0x6813869c3e5dec06e6f88b42d41487dc5d7abf57",
    signingContract: "0xf1c82c082af3de3614771105f01dc419c3163352",
    paymentToken: "0x07E49Ad54FcD23F6e7B911C2068F0148d1827c08", // NESOLET
    characterNFT: "0xcE8e48Fae05c093a4A1a1F569BDB53313D765937",
    itemNFT: "0x43DCff2A0cedcd5e10e6f1c18b503498dDCe60d5",
  },

  // Redis
  redis: {
    url: process.env.REDIS_URL || "redis://localhost:6379/0",
  },

  // Indexer
  indexer: {
    startBlock: parseInt(process.env.INDEXER_START_BLOCK || "0"),
    pollInterval: parseInt(process.env.INDEXER_POLL_INTERVAL || "2000"), // ms
    batchSize: 100, // blocks per query
    maxRetries: 5,
  },

  // Database
  dbPath: process.env.DB_PATH || "../backend/mapleguard.db",
};
