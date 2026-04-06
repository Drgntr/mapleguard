import sys
import json
sys.path.append('.')
from services.market_data import market_data_service

data = market_data_service._get('https://msu.io/marketplace/api/marketplace/items/8371514744002029434355400508674')
print('TOP KEYS:', list(data.keys()))
for k, v in data.items():
    if not isinstance(v, dict):
        print(f'  {k}: {v}')
