"""Pydantic models for seedrank.config.yaml."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Feature(BaseModel):
    """A product feature with its current status."""

    name: str
    status: str = Field(description="One of: live, in_development, planned, early_access")
    description: str = ""

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"live", "in_development", "planned", "early_access"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}, got '{v}'")
        return v

    @property
    def status_label(self) -> str:
        return {
            "live": "LIVE",
            "in_development": "IN DEVELOPMENT",
            "planned": "PLANNED",
            "early_access": "EARLY ACCESS",
        }[self.status]


class ProductConfig(BaseModel):
    """The product being marketed."""

    name: str
    domain: str
    category: str = Field(default="SaaS", description="Product category, e.g. PaaS, SaaS, DevTool")
    tagline: str = ""
    description: str = ""
    features: list[Feature] = Field(default_factory=list)
    pricing_url: str = ""
    docs_url: str = ""
    signup_url: str = ""

    @property
    def live_features(self) -> list[Feature]:
        return [f for f in self.features if f.status == "live"]

    @property
    def planned_features(self) -> list[Feature]:
        return [f for f in self.features if f.status in ("planned", "in_development")]


class VoiceConfig(BaseModel):
    """Brand voice and writing style rules."""

    tone: list[str] = Field(default_factory=lambda: ["direct", "technical", "confident", "helpful"])
    banned_words: list[str] = Field(
        default_factory=lambda: [
            "supercharge",
            "turbocharge",
            "unleash",
            "revolutionize",
            "game-changing",
            "best-in-class",
            "world-class",
            "cutting-edge",
            "simple and easy",
            "blazing fast",
            "seamless",
            "seamlessly",
            "leverage",
            "utilize",
        ]
    )
    cta_style: str = Field(default="direct", description="CTA style: direct, soft, technical")
    cta_primary: str = "Get started"
    cta_never: list[str] = Field(default_factory=list)


class Persona(BaseModel):
    """A target user persona."""

    slug: str
    name: str
    description: str = ""
    pain_points: list[str] = Field(default_factory=list)
    search_behavior: list[str] = Field(default_factory=list)


class Competitor(BaseModel):
    """A competitor product."""

    slug: str
    name: str
    domain: str
    tier: int = Field(default=1, description="1 = direct competitor, 2 = adjacent")
    strengths: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    positioning_against: str = ""
    verification_urls: dict[str, str] = Field(default_factory=dict)
    last_verified: str = ""
    data_file: str = ""


class ComparisonRules(BaseModel):
    """Rules for comparison / vs articles."""

    require_source_urls: bool = Field(
        default=True,
        description="Require source URLs for all competitor claims",
    )
    require_last_verified: bool = Field(
        default=True,
        description="Require 'last verified' date on comparison data",
    )
    require_disclaimer: bool = Field(
        default=True,
        description="Require editorial disclaimer on comparison articles",
    )
    disclaimer_text: str = Field(
        default=(
            "We research and fact-check every claim in our articles. Pricing and"
            " features may change; we update periodically. If you spot an"
            " inaccuracy, email {corrections_email}."
        ),
        description="Disclaimer template. {corrections_email} is replaced at render time.",
    )
    banned_claims: list[str] = Field(
        default_factory=list,
        description="Claims you must never make about competitors (e.g. 'worst product')",
    )


class DisclaimerTemplate(BaseModel):
    """A reusable disclaimer template for specific content types."""

    slug: str
    label: str
    template_text: str
    use_when: str = ""


def _default_disclaimer_templates() -> list[DisclaimerTemplate]:
    """Return the 7 default disclaimer templates (genericized)."""
    return [
        DisclaimerTemplate(
            slug="comparison",
            label="Standard Comparison",
            template_text=(
                "**Editorial note:** We research and fact-check every claim in our"
                " comparison articles. Pricing, features, and availability may change;"
                " we update periodically. If you spot an inaccuracy, email"
                " {corrections_email}."
            ),
            use_when="Any article that compares your product with one or more competitors.",
        ),
        DisclaimerTemplate(
            slug="pricing",
            label="Pricing Comparison",
            template_text=(
                "**Pricing disclaimer:** All pricing information was verified on the"
                " dates noted. Prices may change without notice. Please verify current"
                " pricing on each provider's official website before making a decision."
                " If you spot an error, email {corrections_email}."
            ),
            use_when="Articles that include specific pricing numbers or plan comparisons.",
        ),
        DisclaimerTemplate(
            slug="feature",
            label="Feature Comparison",
            template_text=(
                "**Feature comparison note:** Feature availability and capabilities were"
                " verified on the dates noted. Products evolve continuously — check each"
                " provider's documentation for current capabilities. Report inaccuracies"
                " to {corrections_email}."
            ),
            use_when="Articles with feature comparison tables or detailed feature analysis.",
        ),
        DisclaimerTemplate(
            slug="exclusivity",
            label="Exclusivity Claim",
            template_text=(
                "**Note:** To the best of our knowledge as of the date noted, this"
                " capability distinction is accurate. The market evolves quickly — if"
                " you know of another provider offering this, please let us know at"
                " {corrections_email}."
            ),
            use_when="When claiming your product is the only one offering a specific capability.",
        ),
        DisclaimerTemplate(
            slug="statistics",
            label="Competitor Statistics",
            template_text=(
                "**Data note:** Statistics cited in this article come from publicly"
                " available sources as of the dates noted. We do not have access to"
                " competitors' internal data. If any figure is incorrect, email"
                " {corrections_email}."
            ),
            use_when="When citing competitor user counts, revenue, or other statistics.",
        ),
        DisclaimerTemplate(
            slug="alternative",
            label="Alternative Page",
            template_text=(
                "**Editorial note:** This article compares {company_name} with"
                " alternatives. We aim to present each option fairly based on publicly"
                " available information. Pricing and features were verified on the dates"
                " noted. Report inaccuracies to {corrections_email}."
            ),
            use_when="'Alternative to X' pages listing multiple competitors.",
        ),
        DisclaimerTemplate(
            slug="listicle",
            label="Listicle",
            template_text=(
                "**Editorial note:** Rankings and recommendations reflect our editorial"
                " opinion based on publicly available information as of the date noted."
                " We periodically re-evaluate. Report inaccuracies to"
                " {corrections_email}."
            ),
            use_when="'Top N' or 'Best X for Y' listicle articles.",
        ),
    ]


class LegalConfig(BaseModel):
    """Legal compliance settings."""

    company_name: str = ""
    corrections_email: str = ""
    data_staleness_days: int = Field(
        default=90,
        description="Max age in days before competitor data is flagged as stale",
    )
    require_affiliate_disclosure: bool = Field(
        default=False,
        description="Require FTC affiliate disclosure when linking to products",
    )
    affiliate_disclosure_text: str = Field(
        default=(
            "Some links in this article are affiliate links. We may earn a commission"
            " at no extra cost to you."
        ),
    )
    comparison: ComparisonRules = Field(default_factory=ComparisonRules)
    disclaimer_templates: list[DisclaimerTemplate] = Field(
        default_factory=_default_disclaimer_templates,
    )


class DataForSeoConfig(BaseModel):
    """DataForSEO API configuration."""

    login: str = Field(default="", description="API login or set DATAFORSEO_LOGIN env var")
    password: str = Field(default="", description="API password or set DATAFORSEO_PASSWORD env var")
    location: int = Field(default=2840, description="Location code (2840 = US)")
    language: str = Field(default="en", description="Language code")


class GSCConfig(BaseModel):
    """Google Search Console configuration."""

    property_url: str = Field(
        default="", description="GSC property URL, e.g. sc-domain:example.com"
    )
    credentials_path: str = Field(
        default="credentials.json",
        description="Path to OAuth credentials JSON file",
    )


class AIModelConfig(BaseModel):
    """An AI model for GEO queries."""

    slug: str
    model: str = Field(description="Model identifier, e.g. gpt-4o, claude-sonnet-4-20250514")
    api_key_env: str = Field(description="Environment variable name for API key")
    endpoint: str = Field(
        default="",
        description="Custom endpoint URL (for Perplexity, Gemini, etc.)",
    )
    provider: str = Field(
        default="openai",
        description="Provider: openai, anthropic, perplexity, gemini",
    )


class ContentType(BaseModel):
    """A page type definition."""

    slug: str
    route: str = Field(description="URL pattern, e.g. /blog/[slug]")
    content_dir: str = Field(description="Directory under content/")
    label: str = Field(description="Human-readable name")
    min_words: int = 800


class PseoConfig(BaseModel):
    """Top-level configuration for a pSEO workspace."""

    product: ProductConfig
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    personas: list[Persona] = Field(default_factory=list)
    competitors: list[Competitor] = Field(default_factory=list)
    content_types: list[ContentType] = Field(default_factory=list)
    legal: LegalConfig = Field(default_factory=LegalConfig)
    dataforseo: DataForSeoConfig = Field(default_factory=DataForSeoConfig)
    gsc: GSCConfig = Field(default_factory=GSCConfig)
    ai_models: list[AIModelConfig] = Field(default_factory=list)

    @property
    def tier1_competitors(self) -> list[Competitor]:
        return [c for c in self.competitors if c.tier == 1]

    @property
    def tier2_competitors(self) -> list[Competitor]:
        return [c for c in self.competitors if c.tier == 2]

    @property
    def competitor_by_slug(self) -> dict[str, Competitor]:
        return {c.slug: c for c in self.competitors}
