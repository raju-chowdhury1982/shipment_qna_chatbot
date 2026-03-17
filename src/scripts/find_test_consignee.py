import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)


def find_consignee():
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = "shipment-idx"

    client = SearchClient(
        endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(api_key)
    )

    targets = ["6300150977", "TGBU3507484", "5303013776"]

    for t in targets:
        print(f"\nSearching for target: {t}")
        results = list(client.search(search_text=t, top=1))
        if results:
            doc = results[0]
            codes = doc.get("consignee_code_ids", [])
            print(f"Found match! Consignee codes: {codes}")
        else:
            print("No match found.")


if __name__ == "__main__":
    find_consignee()
