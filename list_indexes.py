import os

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
api_key = os.getenv("AZURE_SEARCH_API_KEY")

cred = AzureKeyCredential(api_key) if api_key else DefaultAzureCredential()
client = SearchIndexClient(endpoint=endpoint, credential=cred)

print("Indexes:")
for index in client.list_indexes():
    print(f"- {index.name}")
