import os

from dotenv import find_dotenv, load_dotenv
from openai import AzureOpenAI

load_dotenv(find_dotenv(), override=True)

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
deployment = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT")

print(f"Endpoint: {endpoint}")
print(f"API Version: {api_version}")
print(f"Deployment: {deployment}")

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=api_key,
    api_version=api_version,
)

try:
    print("Testing string input...")
    res = client.embeddings.create(input="hello world", model=deployment)
    print("String input success!")
except Exception as e:
    print(f"String input failed: {e}")

try:
    print("Testing list input...")
    res = client.embeddings.create(input=["hello world"], model=deployment)
    print("List input success!")
except Exception as e:
    print(f"List input failed: {e}")
