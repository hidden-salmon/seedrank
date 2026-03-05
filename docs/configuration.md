# Configuration

Seedrank is configured through two files: `seedrank.config.yaml` for product settings, and `.env` for API keys.

## Quick Start Config

The only required fields are `product.name` and `product.domain`:

```yaml
product:
  name: My Product
  domain: myproduct.com
```

Everything else has sensible defaults. Add sections as you need them.

## Full Config Reference

### `product` — Your product info

```yaml
product:
  name: Moonbeam                                   # Required
  domain: moonbeam.example.com                     # Required
  category: Email Marketing                        # Used in content generation
  tagline: "Email that actually gets read."
  description: "AI-powered email marketing."       # Used in schema markup
  pricing_url: "https://moonbeam.example.com/pricing"
  docs_url: "https://docs.moonbeam.example.com"
  signup_url: "https://app.moonbeam.example.com"
  features:
    - name: AI send-time optimization
      status: live                                  # live | in_development | planned | early_access
      description: Sends emails at optimal times.
```

Feature `status` matters for content accuracy:
- `live` — can be claimed as a current feature
- `in_development` — must be qualified ("coming soon", "in development")
- `planned` / `early_access` — must be clearly labeled as not generally available

### `voice` — Brand voice rules

```yaml
voice:
  tone: [direct, friendly, confident, helpful]
  cta_style: direct              # direct | soft | technical
  cta_primary: "Start sending"
  cta_never:                     # CTAs that must never appear
    - "Get Started"
    - "Try it now!"
  banned_words:                  # Words flagged during validation
    - supercharge
    - revolutionize
    - game-changing
    - seamless
    - leverage
```

### `personas` — Target users

```yaml
personas:
  - slug: switcher
    name: The Switcher
    description: "Frustrated with current platform."
    pain_points:
      - "Paying too much"
      - "Poor deliverability"
    search_behavior:
      - "best mailchimp alternative"
      - "cheaper email marketing tool"
```

Personas inform question discovery and content angle during research sessions.

### `competitors` — Competitive landscape

```yaml
competitors:
  - slug: mailchimp
    name: Mailchimp
    domain: mailchimp.com
    tier: 1                      # 1 = direct competitor, 2 = adjacent
    strengths:
      - "Huge brand recognition"
      - "Large template library"
    positioning_against: "Gets expensive fast. We offer better value."
```

Tier 1 competitors are analyzed more deeply during research and require verified data for comparison content.

### `content_types` — Where articles live

```yaml
content_types:
  - slug: blog
    route: "/blog/[slug]"        # URL pattern on your site
    content_dir: blog            # Subdirectory under content/
    label: Blog Posts
    min_words: 1500              # Minimum word count for validation
  - slug: compare
    route: "/compare/[slug]"
    content_dir: compare
    label: Comparison Pages
    min_words: 1000
```

### `legal` — Compliance settings

```yaml
legal:
  company_name: "Moonbeam Inc."
  corrections_email: "corrections@moonbeam.example.com"
  data_staleness_days: 90                    # Flag data older than this
  require_affiliate_disclosure: false
  eu_checks_enabled: false                   # EU unfair competition law checks
  trademark_max_mentions: 15                 # Flag excessive trademark usage
  implied_deficiency_check: true             # Check "no hidden fees" near competitors
  require_comparison_methodology: true       # Require methodology section
  additional_disparaging_words: []           # Extra words to flag
  comparison:
    require_source_urls: true
    require_last_verified: true
    require_disclaimer: true
    disclaimer_text: >-
      We research and fact-check every claim. Pricing and features may change;
      we update periodically. If you spot an inaccuracy, email {corrections_email}.
    banned_claims:
      - "worst email platform"
      - "scam"
```

### `dataforseo` — Keyword research API

```yaml
dataforseo:
  location: 2840                 # 2840 = United States
  language: en
```

Credentials should be set via environment variables (see below), but can also be set here:

```yaml
dataforseo:
  login: your_login
  password: your_password
```

### `gsc` — Google Search Console

```yaml
gsc:
  property_url: "sc-domain:moonbeam.example.com"
  credentials_path: "credentials.json"
```

### `ai_models` — GEO monitoring providers

```yaml
ai_models:
  - slug: chatgpt
    model: gpt-4o
    api_key_env: OPENAI_API_KEY
    provider: openai
  - slug: claude
    model: claude-sonnet-4-20250514
    api_key_env: ANTHROPIC_API_KEY
    provider: anthropic
  - slug: perplexity
    model: sonar
    api_key_env: PERPLEXITY_API_KEY
    provider: perplexity
    endpoint: "https://api.perplexity.ai"
  - slug: gemini
    model: gemini-2.0-flash
    api_key_env: GEMINI_API_KEY
    provider: gemini
```

## Environment Variables

Create a `.env` file in your workspace root. Seedrank loads it automatically.

| Variable | Service | Used by |
|---|---|---|
| `DATAFORSEO_LOGIN` | [DataForSEO](https://dataforseo.com) | `research keywords`, `serp`, `competitors`, `expand` |
| `DATAFORSEO_PASSWORD` | [DataForSEO](https://dataforseo.com) | Same |
| `OPENAI_API_KEY` | [OpenAI](https://platform.openai.com) | `research geo`, `research questions --provider chatgpt` |
| `ANTHROPIC_API_KEY` | [Anthropic](https://console.anthropic.com) | `research geo` (Claude queries) |
| `PERPLEXITY_API_KEY` | [Perplexity](https://docs.perplexity.ai) | `research geo` (Perplexity queries) |
| `GEMINI_API_KEY` | [Google AI](https://ai.google.dev) | `research geo` (Gemini queries) |

Google Search Console uses OAuth instead of an API key — run `seedrank gsc auth`.

## Validating Your Config

```bash
seedrank validate config
```

This checks that required fields are present, feature statuses are valid, competitor slugs match, and content type routes are well-formed.
