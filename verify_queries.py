import json

import requests

BASE_URL = "http://127.0.0.1:8000/api/chat"

test_queries = [
    "give me full milestone of SEGU5935510",
    "can you tell me the weight of the SEGU5935510 and count of items",
    "What is status of 5302997239?",
    "What is status of obl ONEYHKGFD3816700?",
    "What are the POs in the container TCLU4703170?",
    "What is the container carrying the PO 5302997239?",
    "What are the POs arriving in Los Angeles?",
]


def test_query(query):
    payload = {
        "question": query,
        "consignee_codes": ["0025833"],  # Using default code
        "conversation_id": "test-session",
    }
    print(f"\nQUERY: {query}")
    try:
        response = requests.post(BASE_URL, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "NO ANSWER FIELD")
            intent = data.get("intent", "NO INTENT")
            print(f"INTENT: {intent}")
            print(f"ANSWER: {answer[:300]}...")
        else:
            print(f"ERROR: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"EXCEPTION: {e}")


if __name__ == "__main__":
    for q in test_queries:
        test_query(q)
