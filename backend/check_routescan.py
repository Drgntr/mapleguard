import httpx

r = httpx.get('https://api.routescan.io/v2/network/mainnet/evm/68414/erc721-transfers?tokenAddress=0x43DCff2A0cedcd5e10e6f1c18b503498dDCe60d5&limit=1')
data = r.json()
items = data.get('items', [])
if items:
    for k, v in items[0].items():
        print(f"{k} = {v}")


