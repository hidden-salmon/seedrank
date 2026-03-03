"""Competitor profile management — rich JSON profiles for competitor data."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def _competitors_dir(workspace: Path) -> Path:
    """Return the competitors data directory."""
    return workspace / "data" / "competitors"


def get_profile_path(workspace: Path, slug: str) -> Path:
    """Return the path to a competitor's JSON profile."""
    return _competitors_dir(workspace) / f"{slug}.json"


def load_profile(workspace: Path, slug: str) -> dict:
    """Load a competitor's JSON profile.

    Raises:
        FileNotFoundError: If the profile doesn't exist.
    """
    path = get_profile_path(workspace, slug)
    if not path.exists():
        raise FileNotFoundError(f"No competitor profile found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_profile(workspace: Path, slug: str, data: dict) -> None:
    """Save a competitor's JSON profile."""
    path = get_profile_path(workspace, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _skeleton(slug: str, name: str, domain: str) -> dict:
    """Return a skeleton profile structure."""
    return {
        "slug": slug,
        "name": name,
        "url": f"https://{domain}",
        "verification_urls": {
            "pricing": "",
            "docs": "",
            "changelog": "",
            "blog": "",
        },
        "tier": 1,
        "last_verified": "",
        "company": {
            "founded": "",
            "hq": "",
            "employees": "",
            "funding": "",
        },
        "product": {
            "description": "",
            "key_features": [],
        },
        "pricing": {
            "model": "",
            "tiers": [],
            "notes": "",
        },
        "strengths": [],
        "limitations": [],
        "our_positioning": "",
    }


def init_profile(workspace: Path, slug: str, name: str, domain: str) -> Path:
    """Create a skeleton JSON profile for a competitor.

    Returns the path to the created file.
    """
    path = get_profile_path(workspace, slug)
    if path.exists():
        return path  # Don't overwrite existing profiles
    data = _skeleton(slug, name, domain)
    save_profile(workspace, slug, data)
    return path


def check_freshness(workspace: Path, slug: str, max_days: int = 30) -> dict:
    """Check how fresh a competitor profile is.

    Returns:
        {"fresh": bool, "days_old": int | None, "last_verified": str}
    """
    try:
        profile = load_profile(workspace, slug)
    except FileNotFoundError:
        return {"fresh": False, "days_old": None, "last_verified": ""}

    last_verified = profile.get("last_verified", "")
    if not last_verified:
        return {"fresh": False, "days_old": None, "last_verified": ""}

    try:
        verified_dt = datetime.fromisoformat(last_verified.replace("Z", "+00:00"))
        if verified_dt.tzinfo is None:
            verified_dt = verified_dt.replace(tzinfo=UTC)
        days_old = (datetime.now(UTC) - verified_dt).days
        return {
            "fresh": days_old <= max_days,
            "days_old": days_old,
            "last_verified": last_verified,
        }
    except (ValueError, TypeError):
        return {"fresh": False, "days_old": None, "last_verified": last_verified}


def list_profiles(workspace: Path) -> list[dict]:
    """List all competitor profiles with basic info and freshness."""
    competitors_dir = _competitors_dir(workspace)
    if not competitors_dir.exists():
        return []

    profiles = []
    for path in sorted(competitors_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            freshness = check_freshness(workspace, path.stem)
            profiles.append({
                "slug": data.get("slug", path.stem),
                "name": data.get("name", ""),
                "url": data.get("url", ""),
                "tier": data.get("tier", 1),
                "last_verified": freshness["last_verified"],
                "days_old": freshness["days_old"],
                "fresh": freshness["fresh"],
            })
        except (json.JSONDecodeError, OSError):
            profiles.append({
                "slug": path.stem,
                "name": "(error reading profile)",
                "url": "",
                "tier": 0,
                "last_verified": "",
                "days_old": None,
                "fresh": False,
            })
    return profiles
