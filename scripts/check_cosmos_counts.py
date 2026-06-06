"""Check Cosmos DB container document counts.

Usage: python scripts/check_cosmos_counts.py
"""
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(dotenv_path=Path('.') / '.env')

endpoint = os.environ.get('COSMOS_ENDPOINT')
key = os.environ.get('COSMOS_KEY')
database_name = os.environ.get('COSMOS_DATABASE', 'argus-db')

if not endpoint or not key:
    print('Missing COSMOS_ENDPOINT or COSMOS_KEY in .env')
    raise SystemExit(1)

from azure.cosmos import CosmosClient

client = CosmosClient(endpoint, key)
db = client.get_database_client(database_name)

containers = [
    'entities',
    'corporate_graph',
    'transactions',
    'pep_list',
    'kyc_reports',
]
print(f'Database: {database_name}, Checking containers: {containers}')
for cid in containers:
    container = db.get_container_client(cid)
    try:
        query = 'SELECT VALUE COUNT(1) FROM c'
        res = list(container.query_items(query, enable_cross_partition_query=True))
        count = res[0] if res else 0
    except Exception as e:
        count = f'ERROR: {e}'
    print(f'  {cid}: {count}')
