"""Tests for competitor profile management (seedrank.data.competitors)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from seedrank.data.competitors import (
    check_freshness,
    get_profile_path,
    init_profile,
    list_profiles,
    load_profile,
    save_profile,
)


class TestInitProfile:
    """Tests for init_profile — creates skeleton JSON."""

    def test_creates_skeleton_json(self, tmp_path: Path) -> None:
        path = init_profile(tmp_path, "acme", "Acme Corp", "acme.com")
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["slug"] == "acme"
        assert data["name"] == "Acme Corp"
        assert data["url"] == "https://acme.com"

    def test_returns_path(self, tmp_path: Path) -> None:
        path = init_profile(tmp_path, "acme", "Acme Corp", "acme.com")
        expected = get_profile_path(tmp_path, "acme")
        assert path == expected

    def test_does_not_overwrite_existing(self, tmp_path: Path) -> None:
        # Create profile first
        init_profile(tmp_path, "acme", "Acme Corp", "acme.com")
        # Modify the file to detect overwrite
        profile_path = get_profile_path(tmp_path, "acme")
        data = json.loads(profile_path.read_text(encoding="utf-8"))
        data["name"] = "Modified Name"
        profile_path.write_text(json.dumps(data), encoding="utf-8")

        # Re-init should NOT overwrite
        init_profile(tmp_path, "acme", "New Name", "new.com")
        reloaded = json.loads(profile_path.read_text(encoding="utf-8"))
        assert reloaded["name"] == "Modified Name"

    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        ws = tmp_path / "deep" / "workspace"
        # Directory doesn't exist yet
        assert not ws.exists()
        init_profile(ws, "rival", "Rival Inc", "rival.io")
        assert (ws / "data" / "competitors" / "rival.json").exists()


class TestLoadProfile:
    """Tests for load_profile — loads JSON from disk."""

    def test_loads_json(self, tmp_path: Path) -> None:
        init_profile(tmp_path, "acme", "Acme Corp", "acme.com")
        data = load_profile(tmp_path, "acme")
        assert data["slug"] == "acme"
        assert data["name"] == "Acme Corp"
        assert isinstance(data, dict)

    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No competitor profile found"):
            load_profile(tmp_path, "nonexistent")


class TestSaveProfile:
    """Tests for save_profile — saves JSON and creates parent dir."""

    def test_saves_json(self, tmp_path: Path) -> None:
        data = {"slug": "test", "name": "Test", "custom_field": 42}
        save_profile(tmp_path, "test", data)
        loaded = load_profile(tmp_path, "test")
        assert loaded["slug"] == "test"
        assert loaded["custom_field"] == 42

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        ws = tmp_path / "new_workspace"
        assert not ws.exists()
        save_profile(ws, "comp", {"slug": "comp"})
        assert (ws / "data" / "competitors" / "comp.json").exists()

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        save_profile(tmp_path, "x", {"slug": "x", "version": 1})
        save_profile(tmp_path, "x", {"slug": "x", "version": 2})
        loaded = load_profile(tmp_path, "x")
        assert loaded["version"] == 2


class TestCheckFreshness:
    """Tests for check_freshness — fresh/stale/never-verified."""

    def test_fresh_profile(self, tmp_path: Path) -> None:
        now_iso = datetime.now(UTC).isoformat()
        data = {"slug": "fresh", "last_verified": now_iso}
        save_profile(tmp_path, "fresh", data)

        result = check_freshness(tmp_path, "fresh", max_days=30)
        assert result["fresh"] is True
        assert result["days_old"] is not None
        assert result["days_old"] <= 1
        assert result["last_verified"] == now_iso

    def test_stale_profile(self, tmp_path: Path) -> None:
        old_date = (datetime.now(UTC) - timedelta(days=60)).isoformat()
        data = {"slug": "stale", "last_verified": old_date}
        save_profile(tmp_path, "stale", data)

        result = check_freshness(tmp_path, "stale", max_days=30)
        assert result["fresh"] is False
        assert result["days_old"] is not None
        assert result["days_old"] >= 59

    def test_never_verified_empty_string(self, tmp_path: Path) -> None:
        data = {"slug": "nover", "last_verified": ""}
        save_profile(tmp_path, "nover", data)

        result = check_freshness(tmp_path, "nover")
        assert result["fresh"] is False
        assert result["days_old"] is None
        assert result["last_verified"] == ""

    def test_missing_profile(self, tmp_path: Path) -> None:
        result = check_freshness(tmp_path, "ghost")
        assert result["fresh"] is False
        assert result["days_old"] is None
        assert result["last_verified"] == ""

    def test_custom_max_days(self, tmp_path: Path) -> None:
        old_date = (datetime.now(UTC) - timedelta(days=10)).isoformat()
        data = {"slug": "edge", "last_verified": old_date}
        save_profile(tmp_path, "edge", data)

        # 10 days old with max_days=15 => fresh
        assert check_freshness(tmp_path, "edge", max_days=15)["fresh"] is True
        # 10 days old with max_days=5 => stale
        assert check_freshness(tmp_path, "edge", max_days=5)["fresh"] is False


class TestListProfiles:
    """Tests for list_profiles — returns profiles with freshness info."""

    def test_returns_empty_when_no_dir(self, tmp_path: Path) -> None:
        assert list_profiles(tmp_path) == []

    def test_lists_multiple_profiles(self, tmp_path: Path) -> None:
        init_profile(tmp_path, "alpha", "Alpha", "alpha.com")
        init_profile(tmp_path, "beta", "Beta", "beta.com")

        profiles = list_profiles(tmp_path)
        assert len(profiles) == 2
        slugs = {p["slug"] for p in profiles}
        assert slugs == {"alpha", "beta"}

    def test_includes_freshness_info(self, tmp_path: Path) -> None:
        now_iso = datetime.now(UTC).isoformat()
        data = {
            "slug": "fresh-co", "name": "Fresh Co",
            "url": "https://fresh.co", "tier": 1,
            "last_verified": now_iso,
        }
        save_profile(tmp_path, "fresh-co", data)

        profiles = list_profiles(tmp_path)
        assert len(profiles) == 1
        p = profiles[0]
        assert p["slug"] == "fresh-co"
        assert p["name"] == "Fresh Co"
        assert p["fresh"] is True
        assert p["days_old"] is not None

    def test_sorted_alphabetically(self, tmp_path: Path) -> None:
        init_profile(tmp_path, "zeta", "Zeta", "zeta.com")
        init_profile(tmp_path, "alpha", "Alpha", "alpha.com")
        profiles = list_profiles(tmp_path)
        assert profiles[0]["slug"] == "alpha"
        assert profiles[1]["slug"] == "zeta"


class TestSkeletonStructure:
    """Test that skeleton profiles contain the correct keys."""

    def test_skeleton_has_required_keys(self, tmp_path: Path) -> None:
        init_profile(tmp_path, "test", "Test", "test.com")
        data = load_profile(tmp_path, "test")

        expected_top_keys = {
            "slug", "name", "url", "verification_urls", "tier",
            "last_verified", "company", "product", "pricing",
            "strengths", "limitations", "our_positioning",
        }
        assert set(data.keys()) == expected_top_keys

    def test_skeleton_verification_urls_keys(self, tmp_path: Path) -> None:
        init_profile(tmp_path, "test", "Test", "test.com")
        data = load_profile(tmp_path, "test")
        assert set(data["verification_urls"].keys()) == {"pricing", "docs", "changelog", "blog"}

    def test_skeleton_company_keys(self, tmp_path: Path) -> None:
        init_profile(tmp_path, "test", "Test", "test.com")
        data = load_profile(tmp_path, "test")
        assert set(data["company"].keys()) == {"founded", "hq", "employees", "funding"}

    def test_skeleton_product_keys(self, tmp_path: Path) -> None:
        init_profile(tmp_path, "test", "Test", "test.com")
        data = load_profile(tmp_path, "test")
        assert set(data["product"].keys()) == {"description", "key_features"}
        assert isinstance(data["product"]["key_features"], list)

    def test_skeleton_pricing_keys(self, tmp_path: Path) -> None:
        init_profile(tmp_path, "test", "Test", "test.com")
        data = load_profile(tmp_path, "test")
        assert set(data["pricing"].keys()) == {"model", "tiers", "notes"}
        assert isinstance(data["pricing"]["tiers"], list)

    def test_skeleton_default_values(self, tmp_path: Path) -> None:
        init_profile(tmp_path, "test", "Test", "test.com")
        data = load_profile(tmp_path, "test")
        assert data["tier"] == 1
        assert data["last_verified"] == ""
        assert data["strengths"] == []
        assert data["limitations"] == []
        assert data["our_positioning"] == ""
