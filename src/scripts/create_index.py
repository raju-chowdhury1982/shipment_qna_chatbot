import os
import sys

# Ensure src is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (HnswAlgorithmConfiguration,
                                                   ScoringProfile, SearchField,
                                                   SearchFieldDataType,
                                                   SearchIndex,
                                                   SemanticConfiguration,
                                                   SemanticField,
                                                   SemanticPrioritizedFields,
                                                   SemanticSearch, SimpleField,
                                                   TextWeights, VectorSearch,
                                                   VectorSearchProfile)
from dotenv import find_dotenv, load_dotenv

from scripts.schema_definitions import SCHEMA_FIELDS

load_dotenv(find_dotenv(), override=True)


def _map_type(type_name: str) -> SearchFieldDataType:
    mapping = {
        "String": SearchFieldDataType.String,
        "Boolean": SearchFieldDataType.Boolean,
        "Double": SearchFieldDataType.Double,
        "Int32": SearchFieldDataType.Int32,
        "Int64": SearchFieldDataType.Int64,
        "DateTimeOffset": SearchFieldDataType.DateTimeOffset,
        "Collection(String)": SearchFieldDataType.Collection(
            SearchFieldDataType.String
        ),
    }
    if type_name not in mapping:
        raise ValueError(f"Unknown type_name: {type_name}")
    return mapping[type_name]


def create_index():
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = "shipment-idx"

    if not endpoint:
        print("Missing AZURE_SEARCH_ENDPOINT")
        return

    cred = AzureKeyCredential(api_key) if api_key else DefaultAzureCredential()
    client = SearchIndexClient(endpoint=endpoint, credential=cred)

    # 1. Dynamically Construct Fields from Schema
    fields = []
    for fdef in SCHEMA_FIELDS:
        # Document ID is a special Key field
        if fdef.name == "document_id":
            fields.append(
                SimpleField(
                    name=fdef.name,
                    type=_map_type(fdef.type_name),
                    key=True,
                    filterable=fdef.filterable,
                )
            )
            continue

        # Simple Fields don't need analyzer/searchable configs overhead
        if (
            not fdef.searchable
            and fdef.type_name != "String"
            and fdef.type_name != "Collection(String)"
        ):
            fields.append(
                SimpleField(
                    name=fdef.name,
                    type=_map_type(fdef.type_name),
                    filterable=fdef.filterable,
                    sortable=fdef.sortable,
                )
            )
        else:
            fields.append(
                SearchField(
                    name=fdef.name,
                    type=_map_type(fdef.type_name),
                    searchable=fdef.searchable,
                    filterable=fdef.filterable,
                    sortable=fdef.sortable,
                )
            )

    # 2. Add Vector Field
    fields.append(
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,  # Default for text-embedding-ada-002 / text-embedding-3-small
            vector_search_profile_name="my-vector-profile",
        )
    )

    # 3. Add Raw Metadata JSON dump (non-searchable/filterable)
    fields.append(
        SearchField(
            name="metadata_json",
            type=SearchFieldDataType.String,
            searchable=False,
            filterable=False,
        )
    )

    # Configure Vector Search
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="my-hnsw")],
        profiles=[
            VectorSearchProfile(
                name="my-vector-profile", algorithm_configuration_name="my-hnsw"
            ),
        ],
    )

    # Configure Scoring profiles (Boost content search)
    scoring_profiles = [
        ScoringProfile(
            name="logistics-score",
            text_weights=TextWeights(weights={"content": 2.5}),
        )
    ]

    # Configure Semantic Search (For hybrid retrieval)
    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="default",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="content")],
                ),
            )
        ]
    )

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        scoring_profiles=scoring_profiles,
        semantic_search=semantic_search,
    )

    print(f"Deleting index '{index_name}' if it exists...")
    try:
        client.delete_index(index_name)
        print(f"Index '{index_name}' deleted.")
    except Exception as e:
        print(f"Index '{index_name}' not found or could not be deleted: {e}")

    print(f"Creating index '{index_name}'...")
    try:
        result = client.create_index(index)
        print(f"Index '{result.name}' created successfully.")
    except Exception as e:
        print(f"Failed to create index: {e}")


if __name__ == "__main__":
    create_index()
