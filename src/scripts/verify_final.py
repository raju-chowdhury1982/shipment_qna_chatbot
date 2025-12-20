import os
import sys

from dotenv import find_dotenv, load_dotenv

# Ensure src is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shipment_qna_bot.tools.azure_ai_search import AzureAISearchTool
from shipment_qna_bot.tools.azure_openai_embeddings import \
    AzureOpenAIEmbeddingsClient

load_dotenv(find_dotenv(), override=True)


def verify():
    print("--- Final Verification ---")
    embedder = AzureOpenAIEmbeddingsClient()
    search_tool = AzureAISearchTool()

    query = "status of shipment"
    consignee_codes = ["0042485"]  # One of the codes I saw in logs

    print(f"Query: {query}")
    print(f"Allowed Consignee Codes: {consignee_codes}")

    try:
        # 1. Test Embedding
        print("Test 1: Generating embedding...")
        vector = embedder.embed_query(query)
        print(f"Success! Vector length: {len(vector)}")

        # 2. Test Search (Hybrid)
        print("Test 2: Performing hybrid search with RLS filter...")
        results = search_tool.search(
            query_text=query, consignee_codes=consignee_codes, vector=vector, top_k=5
        )

        print(f"Search Success! Hits: {len(results['hits'])}")
        for i, hit in enumerate(results["hits"]):
            print(f"  Hit {i+1}: ID={hit.get('document_id')}, Score={hit.get('score')}")
            # print(f"  Snippet: {hit.get('content')[:100]}...")

    except Exception as e:
        print(f"FAILED! Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    verify()
