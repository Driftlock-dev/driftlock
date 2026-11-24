import re
from typing import Any

SENSITIVE_KEY_PATTERN = re.compile(
    r"(token|secret|password|passwd|api_?key|auth|bearer|signature|ssn|card|cvv|iban)",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def redact_payload(data: Any, key_name: str = "") -> Any:
    if isinstance(data, dict):
        return {k: redact_payload(v, k) for k, v in data.items()}
    if isinstance(data, list):
        return [redact_payload(item, key_name) for item in data]
    if isinstance(data, str):
        if key_name and SENSITIVE_KEY_PATTERN.search(key_name):
            return "[REDACTED_SECRET]"
        if EMAIL_PATTERN.fullmatch(data.strip()):
            return "[REDACTED_EMAIL]"
        if data.startswith(("sk_live_", "sk_test_", "whsec_", "ghp_", "eyJ")):
            return "[REDACTED_TOKEN]"
    return data