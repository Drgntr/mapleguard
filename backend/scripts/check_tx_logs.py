"""Check transaction logs for a real NFT sale to verify OrderMatched topic."""
from eth_hash.auto import keccak
import httpx, json

# Compute expected topic
sig = b'OrderMatched(bytes32,address,address,uint256,address,address,uint256,uint256)'
topic = '0x' + keccak(sig).hex()
print('Expected OrderMatched topic:', topic)

# Get a recent ERC-721 transfer
r = httpx.get(
    'https://api.routescan.io/v2/network/mainnet/evm/68414/erc721-transfers'
    '?tokenAddress=0x43DCff2A0cedcd5e10e6f1c18b503498dDCe60d5&limit=1',
    timeout=8
)
items = r.json().get('items', [])
if not items:
    print('No ERC-721 transfers found')
    exit()

tx = items[0].get('txHash', '')
print('txHash:', tx)

# Get tx receipt
r2 = httpx.get(
    'https://api.routescan.io/v2/network/mainnet/evm/68414/etherscan/api',
    params={
        'module': 'proxy',
        'action': 'eth_getTransactionReceipt',
        'txhash': tx,
    },
    timeout=12
)
receipt = r2.json().get('result', {})
logs = receipt.get('logs', [])
print(f'Total logs in tx: {len(logs)}')
for i, log in enumerate(logs):
    addr = log.get('address', '')
    topics = log.get('topics', [''])
    data = log.get('data', '')
    print(f'  Log {i}: addr={addr}')
    print(f'    topic0={topics[0] if topics else "?"}')
    print(f'    topics count={len(topics)}')
    print(f'    data={data[:80]}')
