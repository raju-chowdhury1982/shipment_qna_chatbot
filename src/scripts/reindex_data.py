import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

# Ensure src is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from scripts.schema_definitions import SCHEMA_FIELDS
from shipment_qna_bot.tools.azure_ai_search import AzureAISearchTool
from shipment_qna_bot.tools.azure_openai_embeddings import \
    AzureOpenAIEmbeddingsClient


def load_data(file_path: str) -> List[Dict[str, Any]]:
    documents = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                documents.append(record)
            except json.JSONDecodeError as e:
                print(f"Skipping invalid line: {e}")
    return documents


def to_list(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        flat = []
        for item in val:
            if isinstance(item, str) and "," in item:
                flat.extend([s.strip() for s in item.split(",") if s.strip()])
            elif item is not None:
                flat.append(str(item))
        return list(set(flat))
    if isinstance(val, str):
        if "," in val:
            return [s.strip() for s in val.split(",") if s.strip()]
        return [val.strip()]
    return [str(val)]


def to_float(val: Any) -> Any:
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def to_bool(val: Any) -> Any:
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes", "y")
    return bool(val)


def _normalize_dt(val: Any) -> Any:
    if val is None:
        return None
    try:
        if str(val).strip().lower() in {"nat", "nan", "none", ""}:
            return None
    except Exception:
        pass
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        if s.lower() in {"nat", "nan", "none"}:
            return None
        if s.endswith("Z") or re.search(r"[+-]\d\d:\d\d$", s):
            return s
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
                return s + "T00:00:00Z"
            if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", s):
                return s + "Z"
            return s
    return val


def flatten_document(
    doc: Dict[str, Any], embedder: AzureOpenAIEmbeddingsClient
) -> Dict[str, Any]:
    metadata = doc.get("metadata", {})
    content = doc.get("content", "")
    doc_id = doc.get("document_id")

    if not doc_id or not content or not isinstance(metadata, dict):
        raise ValueError(
            "Invalid JSONL schema. Require document_id, content, and metadata dict."
        )

    # Resolve core values
    consignee_codes = metadata.get("consignee_codes", [])
    if not consignee_codes:
        raw = doc.get("consignee_code")
        if raw:
            try:
                consignee_codes = json.loads(raw.replace("'", '"'))
            except:
                consignee_codes = [raw]
    if not consignee_codes:
        raise ValueError("Missing consignee_codes for RLS.")

    doc["consignee_code_ids"] = consignee_codes

    # Generate Embeddings
    print(f"Generating embedding for doc {doc_id}...")
    vector = embedder.embed_query(content)

    flattened = {
        "metadata_json": json.dumps(metadata),
        "content_vector": vector,
    }

    # Dynamically apply logic based on our unified schema dictionary
    for fdef in SCHEMA_FIELDS:
        name = fdef.name

        # Pull value directly from root if defined
        if name in doc and name != "metadata":
            raw_val = doc[name]
        else:
            # Fallback to checking metadata
            raw_val = None

            # Check custom mapping first (which can be a single string or a list of fallback strings)
            if fdef.source_keys:
                if isinstance(fdef.source_keys, list):
                    for k in fdef.source_keys:
                        if k in metadata and metadata[k] is not None:
                            raw_val = metadata[k]
                            break
                else:
                    raw_val = metadata.get(fdef.source_keys)

            # Lastly, attempt exact name match from metadata
            if raw_val is None:
                raw_val = metadata.get(name)

        # Apply Type Casting
        val = None
        if fdef.type_name == "Collection(String)":
            val = to_list(raw_val)
        elif fdef.type_name == "DateTimeOffset":
            val = _normalize_dt(raw_val)
        elif fdef.type_name == "Boolean":
            val = to_bool(raw_val)
        elif fdef.type_name == "Double":
            val = to_float(raw_val)
        else:  # String
            val_str = str(raw_val) if raw_val is not None else None
            # Do not upload "None" strings, keep json nulls
            if val_str is None or val_str.strip().lower() in ("", "nan", "null"):
                val = None
            else:
                val = val_str

        flattened[name] = val

    return flattened


def _deadletter_path(data_dir: str, file_name: str) -> str:
    failed_dir = os.path.join(data_dir, "failed")
    os.makedirs(failed_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(file_name))[0]
    return os.path.join(failed_dir, f"{base}.failed.jsonl")


def write_deadletter(data_dir: str, file_name: str, errors: list[dict]) -> str:
    path = _deadletter_path(data_dir, file_name)
    with open(path, "w", encoding="utf-8") as f:
        for err in errors:
            f.write(json.dumps(err, ensure_ascii=True) + "\n")
    return path


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest JSONL data into Azure Search index."
    )
    parser.add_argument(
        "file_name",
        nargs="?",
        default="shipment_dec25.jsonl",
        help="Name of the file in data/ directory",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Upload docs that processed successfully even if some failed. Writers dead-letter for failures.",
    )
    args = parser.parse_args()

    data_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", args.file_name
    )
    if not os.path.exists(data_path):
        print(f"Data file not found: {data_path}")
        return

    raw_docs = load_data(data_path)
    print(f"Loaded {len(raw_docs)} documents from {args.file_name}.")

    embedder = AzureOpenAIEmbeddingsClient()

    processed_docs = []
    errors: list[dict] = []
    print(
        f"Starting processing and embedding (this may take a few minutes for {len(raw_docs)} docs)..."
    )

    for i, d in enumerate(raw_docs):
        try:
            processed_docs.append(flatten_document(d, embedder))
            if (i + 1) % 100 == 0:
                print(f"Processed {i+1}/{len(raw_docs)} docs...")
        except Exception as e:
            errors.append(
                {
                    "document_id": d.get("document_id"),
                    "error": str(e),
                    "document": d,
                }
            )
            print(f"Failed to process doc {d.get('document_id')}: {e}")

    if errors:
        deadletter = write_deadletter(
            os.path.dirname(data_path), args.file_name, errors
        )
        print(f"ERROR: {len(errors)} docs failed. Wrote dead-letter to {deadletter}.")
        if not args.allow_partial:
            return

    print(f"Uploading {len(processed_docs)} docs to the index...")
    tool = AzureAISearchTool()
    try:
        tool.upload_documents(processed_docs)
        print("Full re-indexing complete!")
    except Exception as e:
        print(f"Upload failed: {e}")


if __name__ == "__main__":
    main()
