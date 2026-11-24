import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

GUMROAD_VERIFY_URL = "https://api.gumroad.com/v2/licenses/verify"
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours


def _cache_path() -> Path:
    return Path.home() / ".driftlock" / "license.json"


def _load_cached_key(license_key: str) -> bool:
    path = _cache_path()
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("license_key") == license_key:
            if time.time() - data.get("verified_at", 0) < CACHE_TTL_SECONDS:
                return True
    except Exception:
        return False
    return False


def _save_cached_key(license_key: str) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"license_key": license_key, "verified_at": time.time()}),
        encoding="utf-8",
    )


def verify_pro_license(license_key: Optional[str] = None) -> Tuple[bool, str]:
    if os.environ.get("DRIFTLOCK_DEV_BYPASS") == "1":
        return True, "Dev bypass active"

    key = (license_key or os.environ.get("DRIFTLOCK_LICENSE_KEY") or "").strip()
    product_id = os.environ.get("DRIFTLOCK_GUMROAD_PRODUCT_ID", "").strip()

    if not key:
        return False, "Missing license key. Set DRIFTLOCK_LICENSE_KEY or pass --license-key."

    if _load_cached_key(key):
        return True, "Verified (cached)"

    if not product_id:
        return False, "Missing DRIFTLOCK_GUMROAD_PRODUCT_ID for live verification."

    payload = urllib.parse.urlencode({
        "product_id": product_id,
        "license_key": key,
        "increment_uses_count": "false",
    }).encode("utf-8")

    req = urllib.request.Request(
        GUMROAD_VERIFY_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return False, f"License server unreachable: {exc}"

    purchase = body.get("purchase") or {}
    if body.get("success") and not purchase.get("refunded") and not purchase.get("chargebacked"):
        _save_cached_key(key)
        return True, "Verified via Gumroad"

    return False, body.get("message", "Invalid or inactive license key.")