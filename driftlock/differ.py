from dataclasses import dataclass
from typing import Any, Dict, List
from .schema import infer_schema


@dataclass
class DriftIssue:
    severity: str  # "BREAKING" or "NON_BREAKING"
    path: str
    message: str


def _is_compatible_number(expected: str, actual: str) -> bool:
    # Widening int -> float is usually safe; narrowing float -> int is breaking
    return expected == "float" and actual == "int"


def compare_schemas(expected: Dict[str, Any], actual: Dict[str, Any], path: str = "$") -> List[DriftIssue]:
    issues: List[DriftIssue] = []

    exp_type = expected.get("type", "unknown")
    act_type = actual.get("type", "unknown")
    exp_nullable = expected.get("nullable", False)

    # 1. Handle nullability drift
    if act_type == "null":
        if not exp_nullable and exp_type != "null":
            issues.append(DriftIssue(
                severity="BREAKING",
                path=path,
                message=f"Field became null (expected non-null '{exp_type}')"
            ))
        return issues

    # 2. Type mismatch check
    if exp_type != act_type and exp_type != "unknown":
        if not _is_compatible_number(exp_type, act_type):
            issues.append(DriftIssue(
                severity="BREAKING",
                path=path,
                message=f"Type changed from '{exp_type}' to '{act_type}'"
            ))
            return issues

    # 3. Recurse into objects
    if exp_type == "object" and act_type == "object":
        exp_props = expected.get("properties", {})
        act_props = actual.get("properties", {})

        for key, exp_child in exp_props.items():
            child_path = f"{path}.{key}"
            if key not in act_props:
                issues.append(DriftIssue(
                    severity="BREAKING",
                    path=child_path,
                    message="Required field missing from payload"
                ))
            else:
                issues.extend(compare_schemas(exp_child, act_props[key], child_path))

        for key in act_props:
            if key not in exp_props:
                issues.append(DriftIssue(
                    severity="NON_BREAKING",
                    path=f"{path}.{key}",
                    message=f"New field added (type: '{act_props[key].get('type')}')"
                ))

    # 4. Recurse into lists
    elif exp_type == "list" and act_type == "list":
        exp_items = expected.get("items", {})
        act_items = actual.get("items", {})
        if act_items.get("type") != "unknown":
            issues.extend(compare_schemas(exp_items, act_items, f"{path}[]"))

    return issues


def diff_payload_against_contract(contract_doc: Dict[str, Any], incoming_payload: Any) -> List[DriftIssue]:
    expected_contract = contract_doc.get("contract", contract_doc)
    actual_contract = infer_schema(incoming_payload)
    return compare_schemas(expected_contract, actual_contract)