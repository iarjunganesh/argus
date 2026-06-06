"""
create_cosmos_db.py
Creates the Cosmos DB database and containers for ARGUS.
Run after Azure resources are provisioned.
Usage: python infra/create_cosmos_db.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_NAME = os.getenv("COSMOS_DATABASE", "argus-db")

CONTAINERS = [
    {
        "id": "entities",
        "description": "Individual and corporate entity profiles",
        "partition_key": "/entity_type",
    },
    {
        "id": "corporate_graph",
        "description": "Corporate ownership graph nodes and edges",
        "partition_key": "/entity_id",
    },
    {
        "id": "transactions",
        "description": "Synthetic financial transaction records",
        "partition_key": "/entity_id",
    },
    {
        "id": "pep_list",
        "description": "Politically Exposed Persons list",
        "partition_key": "/nationality",
    },
    {
        "id": "kyc_reports",
        "description": "Completed KYC assessment reports",
        "partition_key": "/report_id",
    },
]


def create_cosmos_db():
    print(f"Creating Cosmos DB database and containers...")

    try:
        from azure.cosmos import CosmosClient, exceptions
        from azure.cosmos.partition_key import PartitionKey

        endpoint = os.environ["COSMOS_ENDPOINT"]
        key      = os.environ["COSMOS_KEY"]
        client   = CosmosClient(endpoint, key)

        # Create database
        try:
            db = client.create_database(DATABASE_NAME)
            print(f"  ✅ Database created: {DATABASE_NAME}")
        except exceptions.CosmosResourceExistsError:
            db = client.get_database_client(DATABASE_NAME)
            print(f"  ℹ️  Database already exists: {DATABASE_NAME}")

        # Create containers
        for container_def in CONTAINERS:
            try:
                db.create_container(
                    id=container_def["id"],
                    partition_key=PartitionKey(path=container_def["partition_key"]),
                    offer_throughput=400,  # minimum within free tier shared budget
                )
                print(f"  ✅ Container created: {container_def['id']}")
            except exceptions.CosmosResourceExistsError:
                print(f"  ℹ️  Container already exists: {container_def['id']}")

        print(f"\nCosmos DB ready: {DATABASE_NAME} ({len(CONTAINERS)} containers)")

    except KeyError as e:
        print(f"  ❌ Missing env var: {e}. Run infra/setup.ps1 first.")
        raise
    except Exception as e:
        print(f"  ❌ Error: {e}")
        raise


if __name__ == "__main__":
    create_cosmos_db()
