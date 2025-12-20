import os

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
api_key = os.getenv("AZURE_SEARCH_API_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")

cred = AzureKeyCredential(api_key) if api_key else DefaultAzureCredential()
client = SearchClient(endpoint=endpoint, index_name=index_name, credential=cred)

results = client.search(search_text="*", top=1)
for doc in results:
    import json

    # Convert to dict and print
    print(json.dumps(doc, indent=2))
