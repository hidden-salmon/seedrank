"""Tests for config loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from seedrank.config.loader import load_config
from seedrank.config.schema import PseoConfig


class TestConfigLoading:
    """Test loading configs from YAML files."""

    def test_load_example_config(self, example_config: PseoConfig) -> None:
        assert example_config.product.name == "Moonbeam"
        assert example_config.product.domain == "moonbeam.example.com"
        assert example_config.product.category == "Email Marketing"

    def test_load_minimal_config(self, minimal_config: PseoConfig) -> None:
        assert minimal_config.product.name == "TestProduct"
        assert minimal_config.product.domain == "test.example.com"
        # Defaults should be applied
        assert minimal_config.voice.cta_primary == "Get started"
        assert "direct" in minimal_config.voice.tone

    def test_missing_product_name_fails(self, tmp_path: Path) -> None:
        config_file = tmp_path / "bad.yaml"
        config_file.write_text(yaml.dump({"product": {"domain": "x.com"}}))
        with pytest.raises(ValueError):
            load_config(config_file)

    def test_missing_config_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yaml")

    def test_invalid_feature_status(self, tmp_path: Path) -> None:
        data = {
            "product": {
                "name": "Test",
                "domain": "test.com",
                "features": [{"name": "X", "status": "invalid_status"}],
            }
        }
        config_file = tmp_path / "bad.yaml"
        config_file.write_text(yaml.dump(data))
        with pytest.raises(ValueError):
            load_config(config_file)


class TestConfigProperties:
    """Test computed properties on config models."""

    def test_tier_filtering(self, example_config: PseoConfig) -> None:
        tier1 = example_config.tier1_competitors
        tier2 = example_config.tier2_competitors
        assert len(tier1) + len(tier2) == len(example_config.competitors)
        assert all(c.tier == 1 for c in tier1)
        assert all(c.tier == 2 for c in tier2)

    def test_competitor_by_slug(self, example_config: PseoConfig) -> None:
        lookup = example_config.competitor_by_slug
        assert "mailchimp" in lookup
        assert lookup["mailchimp"].name == "Mailchimp"

    def test_live_features(self, example_config: PseoConfig) -> None:
        live = example_config.product.live_features
        assert all(f.status == "live" for f in live)
        assert len(live) > 0

    def test_planned_features(self, example_config: PseoConfig) -> None:
        planned = example_config.product.planned_features
        assert all(f.status in ("planned", "in_development") for f in planned)

    def test_feature_status_label(self, example_config: PseoConfig) -> None:
        for f in example_config.product.features:
            assert f.status_label in ("LIVE", "IN DEVELOPMENT", "PLANNED", "EARLY ACCESS")


class TestNewConfigFields:
    """Test new config schema additions."""

    def test_dataforseo_config(self, example_config: PseoConfig) -> None:
        assert example_config.dataforseo.location == 2840
        assert example_config.dataforseo.language == "en"

    def test_gsc_config(self, example_config: PseoConfig) -> None:
        assert "moonbeam" in example_config.gsc.property_url

    def test_ai_models(self, example_config: PseoConfig) -> None:
        assert len(example_config.ai_models) == 4
        slugs = [m.slug for m in example_config.ai_models]
        assert "chatgpt" in slugs
        assert "claude" in slugs

    def test_personas_new_fields(self, example_config: PseoConfig) -> None:
        switcher = next(p for p in example_config.personas if p.slug == "switcher")
        assert len(switcher.pain_points) > 0
        assert len(switcher.search_behavior) > 0

    def test_voice_tone(self, example_config: PseoConfig) -> None:
        assert "direct" in example_config.voice.tone
        assert example_config.voice.cta_style == "direct"

    def test_content_types(self, example_config: PseoConfig) -> None:
        assert len(example_config.content_types) == 3
        blog = next(ct for ct in example_config.content_types if ct.slug == "blog")
        assert blog.min_words == 1500

    def test_legal_comparison_rules(self, example_config: PseoConfig) -> None:
        assert example_config.legal.comparison.require_source_urls is True
        assert example_config.legal.comparison.require_last_verified is True
        assert example_config.legal.comparison.require_disclaimer is True
        assert len(example_config.legal.comparison.banned_claims) == 2

    def test_legal_comparison_defaults(self, minimal_config: PseoConfig) -> None:
        assert minimal_config.legal.comparison.require_source_urls is True
        assert minimal_config.legal.comparison.require_disclaimer is True
        assert minimal_config.legal.data_staleness_days == 90
