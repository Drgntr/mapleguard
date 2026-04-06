/**
 * ABI fragments for the MSU marketplace contracts.
 * Only the events we need to index.
 */

// ERC-721 Transfer event (standard NFT transfer)
export const ERC721_TRANSFER_ABI = [
  "event Transfer(address indexed from, address indexed to, uint256 indexed tokenId)",
];

// Marketplace OrderMatched event
// Emitted when a buy order is successfully matched with a sell listing
export const MARKETPLACE_ABI = [
  "event OrderMatched(bytes32 indexed orderHash, address indexed maker, address indexed taker, uint256 tokenId, address nftAddress, address tokenAddress, uint256 tokenAmount, uint256 listingTime)",
  "event OrderCancelled(bytes32 indexed orderHash, address indexed maker)",
  "event OrderCreated(bytes32 indexed orderHash, address indexed maker, uint256 tokenId, address nftAddress, address tokenAddress, uint256 tokenAmount, uint256 listingTime, uint256 expirationTime)",
];

// ERC-20 Transfer for payment token tracking
export const ERC20_TRANSFER_ABI = [
  "event Transfer(address indexed from, address indexed to, uint256 value)",
];
