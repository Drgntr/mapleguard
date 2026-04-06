import httpx, json

# Test cursor-based pagination on the ERC-721 transfers endpoint
# The RouteScan API returns a 'link' field with the next page cursor
r = httpx.get('https://api.routescan.io/v2/network/mainnet/evm/68414/erc721-transfers?tokenAddress=0x43DCff2A0cedcd5e10e6f1c18b503498dDCe60d5&limit=5')
d = r.json()

out = [
    f"Top-level keys: {list(d.keys())}",
    f"link field: {d.get('link')}",
    f"nextToken: {d.get('nextToken')}",
    f"count: {d.get('count')}",
    f"items[0] txHash: {d['items'][0].get('txHash') if d.get('items') else 'N/A'}",
    f"items[0] all keys: {list(d['items'][0].keys()) if d.get('items') else 'N/A'}",
]

with open('pagination_test.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('\n'.join(out))
