import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)

for key in ["AZURE_SEARCH_CONSIGNEE_FIELD", "AZURE_SEARCH_CONSIGNEE_IS_COLLECTION"]:
    print(f"{key}={os.getenv(key)}")
