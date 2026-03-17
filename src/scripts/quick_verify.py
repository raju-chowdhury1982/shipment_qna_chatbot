import json
import time

import requests

# Consignee code for the test documents we found (e.g., Job VN2SSA5554)
TEST_CONSIGNEE_CODES = [
    "0000866",
    "0001363",
    "0001540",
    "0001615",
    "0002679",
    "0002990",
    "0003427",
    "0003905",
    "0004932",
    "0005052",
    "0005053",
    "0005056",
    "0005171",
    "0005176",
    "0009633",
    "0013505",
    "0021472",
    "0023453",
    "0028662",
    "0028664",
    "0029594",
    "0030961",
    "0030962",
    "0037361",
    "0048392",
]

QUERIES = [
    "What is status of 6300150977?",
    "What is status of the PO 6300150977?",
    "What is the delivery status of PO 6300150977",
    "What are the POs in the container TGBU3507484",
    "What is the container carrying the PO 5303013776?",
]


def run_quick_verify():
    api_url = "http://127.0.0.1:8000/api/chat"
    conversation_id = f"verify-{int(time.time())}"

    print(f"Starting Quick Verification with conversation_id: {conversation_id}")
    print(f"Total queries: {len(QUERIES)}")
    print("-" * 50)

    for i, query in enumerate(QUERIES):
        print(f"\n[{i+1}/{len(QUERIES)}] Query: {query}")

        payload = {
            "question": query,
            "consignee_codes": TEST_CONSIGNEE_CODES,
            "conversation_id": conversation_id,
        }

        try:
            start_time = time.time()
            response = requests.post(api_url, json=payload, timeout=120)
            latency = (time.time() - start_time) * 1000
            response.raise_for_status()
            data = response.json()

            print(f"  -> Intent: {data.get('intent', 'N/A')}")
            print(f"  -> Latency: {latency:.2f}ms")
            print(f"  -> Answer: {data.get('answer', '')[:200]}...")

        except Exception as e:
            print(f"  -> ERROR: {str(e)}")

    print("-" * 50)
    print("Verification complete.")


if __name__ == "__main__":
    run_quick_verify()
