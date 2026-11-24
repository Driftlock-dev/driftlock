import json
from typing import Any, Dict


def _infer_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def infer_schema(data: Any) -> Dict[str, Any]:
    """Recursively infers a DriftLock JSON contract from a sample payload."""
    dtype = _infer_type(data)

    if dtype == "object":
        properties = {}
        for key, val in sorted(data.items()):
            properties[key] = infer_schema(val)
        return {
            "type": "object",
            "nullable": False,
            "properties": properties,
        }

    if dtype == "list":
        if not data:
            return {"type": "list", "nullable": False, "items": {"type": "unknown", "nullable": True}}
        # Infer item contract from the first non-null element, or merge object keys across items
        first_non_null = next((item for item in data if item is not None), None)
        if first_non_null is None:
            return {"type": "list", "nullable": False, "items": {"type": "null", "nullable": True}}

        item_schema = infer_schema(first_non_null)
        if item_schema["type"] == "object":
            merged_props = dict(item_schema["properties"])
            for item in data[1:]:
                if isinstance(item, dict):
                    sub = infer_schema(item)["properties"]
                    for k, v in sub.items():
                        if k not in merged_props:
                            v["nullable"] = True
                            merged_props[k] = v
                        elif merged_props[k]["type"] == "null" and v["type"] != "null":
                            v["nullable"] = True
                            merged_props[k] = v
            item_schema["properties"] = merged_props

        return {
            "type": "list",
            "nullable": False,
            "items": item_schema,
        }

    return {
        "type": dtype,
        "nullable": dtype == "null",
    }


def save_contract(payload: Any, output_path: str) -> None:
    contract = {
        "driftlock_version": "1.0",
        "contract": infer_schema(payload),
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(contract, f, indent=2)