import os

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
api_key = os.getenv("AZURE_SEARCH_API_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")

cred = AzureKeyCredential(api_key) if api_key else DefaultAzureCredential()
client = SearchIndexClient(endpoint=endpoint, credential=cred)

index = client.get_index(index_name)

print(f"Index: {index.name}")


def print_fields(fields, indent=""):
    for field in fields:
        attr = []
        if getattr(field, "filterable", False):
            attr.append("F")
        if getattr(field, "searchable", False):
            attr.append("S")
        if getattr(field, "facetable", False):
            attr.append("facet")
        if getattr(field, "sortable", False):
            attr.append("sort")
        print(f"{indent}- {field.name} ({field.type}) [{','.join(attr)}]")
        if field.type == "Edm.ComplexType" or (
            hasattr(field, "fields") and field.fields
        ):
            print_fields(field.fields, indent + "  ")


print_fields(index.fields)
