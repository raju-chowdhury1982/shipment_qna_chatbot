import json
import os

from dotenv import find_dotenv, load_dotenv

try:
    from azure.storage.blob import BlobServiceClient
except ImportError:
    print("Missing azure-storage-blob")
    exit(1)

load_dotenv(find_dotenv(), override=True)

conn_str = os.getenv("AZURE_STORAGE_CONN_STR") or os.getenv(
    "AZURE_STORAGE_CONNECTION_STRING"
)
container_name = os.getenv("AZURE_STORAGE_CONTAINER_UPLD", "shipment-csv-data")

if not conn_str:
    print("No connection string found.")
    exit(1)

blob_service = BlobServiceClient.from_connection_string(conn_str)
container = blob_service.get_container_client(container_name)

for blob in container.list_blobs():
    name = blob.name
    if name and name.lower().endswith(".jsonl"):
        print(f"Reading from {name}")
        blob_client = container.get_blob_client(name)
        stream = blob_client.download_blob(
            offset=0, length=100000
        )  # Download first 100KB
        content = stream.readall().decode("utf-8")
        first_line = content.split("\n")[0]
        data = json.loads(first_line)
        print("Fields in the JSONL:")
        for key in data.keys():
            print(f"- {key}")

        print("\nFull JSON object:")
        print(json.dumps(data, indent=2))
        break
