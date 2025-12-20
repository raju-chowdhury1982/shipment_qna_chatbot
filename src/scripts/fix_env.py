import os

from dotenv import find_dotenv, load_dotenv


def fix_env():
    env_path = find_dotenv()
    if not env_path:
        print("No .env found")
        return

    load_dotenv(env_path, override=True)

    # 1. Fix OpenAI Endpoint
    raw_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    fixed_endpoint = raw_endpoint
    if "/openai/deployments/" in raw_endpoint:
        fixed_endpoint = raw_endpoint.split("/openai/deployments/")[0]
        if not fixed_endpoint.endswith("/"):
            fixed_endpoint += "/"

    updates = {
        "AZURE_OPENAI_ENDPOINT": fixed_endpoint,
        "AZURE_SEARCH_INDEX_NAME": "shipment-idx",
        "AZURE_SEARCH_ID_FIELD": "document_id",
        "AZURE_SEARCH_CONTENT_FIELD": "content",
        "AZURE_SEARCH_CONSIGNEE_FIELD": "consignee_code_ids",
        "AZURE_SEARCH_CONSIGNEE_IS_COLLECTION": "true",
        "AZURE_SEARCH_VECTOR_FIELD": "content_vector",
        "AZURE_OPENAI_API_VERSION": "2024-05-01-preview",  # More stable
    }

    new_lines = []
    keys_updated = set()

    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        parts = stripped.split("=", 1)
        if len(parts) == 2:
            key = parts[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                keys_updated.add(key)
                continue

        new_lines.append(line)

    # Append missing
    for k, v in updates.items():
        if k not in keys_updated:
            new_lines.append(f"{k}={v}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print("Updated .env successfully.")
    for k, v in updates.items():
        print(f"Set {k}={v}")


if __name__ == "__main__":
    fix_env()
