import os

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import (SearchIndexClient,
                                            SearchIndexerClient)
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)


def inspect_live_data():
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")
    # Force check of the indexer target
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "shipment-jsonl-idx")

    if not endpoint or not index_name:
        print("Missing env vars")
        return

    cred = AzureKeyCredential(api_key) if api_key else DefaultAzureCredential()
    index_client = SearchIndexClient(endpoint=endpoint, credential=cred)

    # 0. List all indexes
    print("--- Available Indexes ---")
    try:
        available_indexes = index_client.list_indexes()
        for idx in available_indexes:
            print(f"- {idx.name}")
    except Exception as e:
        print(f"Failed to list indexes: {e}")

    # 1. Check Index Definition (specifically filterable)
    print(f"--- Inspecting Index: {index_name} ---")
    index_client = SearchIndexClient(endpoint=endpoint, credential=cred)
    try:
        index = index_client.get_index(index_name)
        for field in index.fields:
            if field.name == "consignee_code":
                print(f"Field 'consignee_code': Filterable={field.filterable}")
            if field.name == "metadata":
                for sub in field.fields:
                    if sub.name == "consignee_codes":
                        print(
                            f"Field 'metadata/consignee_codes': Filterable={sub.filterable}"
                        )
    except Exception as e:
        print(f"Failed to get index def: {e}")

    # 1.5 Check Indexers
    print("\n--- Inspecting Indexers ---")
    indexer_client = SearchIndexerClient(endpoint=endpoint, credential=cred)
    try:
        indexers = indexer_client.get_indexers()
        found_indexer = False
        for idxr in indexers:
            found_indexer = True
            print(f"Indexer: {idxr.name} (Target Index: {idxr.target_index_name})")
            try:
                status = indexer_client.get_indexer_status(idxr.name)
                print(f"  Status: {status.status}")
                print(
                    f"  Last Result: {status.last_result.status if status.last_result else 'N/A'}"
                )
                if status.last_result and status.last_result.error_message:
                    print(f"  Error: {status.last_result.error_message}")
            except Exception as s_err:
                print(f"  Failed to get status: {s_err}")
        if not found_indexer:
            print("No indexers found.")
    except Exception as e:
        print(f"Failed to list indexers: {e}")

    # 2. Check Data
    print("\n--- Checking Data ---")
    client = SearchClient(endpoint=endpoint, index_name=index_name, credential=cred)
    try:
        # Search for * (all), take 5
        results = client.search(search_text="*", top=5)
        count = 0
        for doc in results:
            count += 1
            print(f"\nDoc ID: {doc.get('chunk_id')}")
            print(f"Container: {doc.get('metadata', {}).get('container_number')}")
            print(f"Parent ID: {doc.get('parent_id')}")
            print(f"Consignee Code (top): {doc.get('consignee_code')}")

        print(f"\nTotal docs retrieved in sample: {count}")

        # Check specific container we uploaded
        print("\n--- Checking Uploaded Container OOCU8049862 ---")
        specific = client.search(search_text="OOCU8049862", top=1)
        found = False
        for doc in specific:
            found = True
            print("Found uploaded doc!")
            print(f"Consignee Code: {doc.get('consignee_code')}")

        if not found:
            print("Uploaded doc NOT found via search.")

    except Exception as e:
        print(f"Search failed: {e}")


if __name__ == "__main__":
    inspect_live_data()
