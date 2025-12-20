import os

from dotenv import find_dotenv, load_dotenv

from shipment_qna_bot.tools.azure_openai_embeddings import \
    AzureOpenAIEmbeddingsClient

load_dotenv(find_dotenv(), override=True)
os.environ["AZURE_OPENAI_API_VERSION"] = "2024-05-01-preview"

try:
    client = AzureOpenAIEmbeddingsClient()
    text = "hello world"
    print(f"Embedding text: {text}")
    vector = client.embed_query(text)
    print(f"Success! Vector length: {len(vector)}")
except Exception as e:
    print(f"Failed! Error: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
