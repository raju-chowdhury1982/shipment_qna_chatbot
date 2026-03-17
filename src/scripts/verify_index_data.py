import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)


def count_docs():
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "shipment-idx")

    client = SearchClient(
        endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(api_key)
    )
    count = client.get_document_count()
    print(f"Index '{index_name}' contains {count} documents.")

    # Peek at one document to see if new fields are populated
    results = list(client.search(search_text="*", top=1))
    if results:
        print("\nPeeking at first document fields:")
        doc = results[0]
        for key, value in doc.items():
            if value and key != "content_vector" and key != "metadata_json":
                print(f"- {key}: {value}")


if __name__ == "__main__":
    count_docs()
