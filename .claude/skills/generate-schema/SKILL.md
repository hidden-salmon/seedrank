---
name: generate-schema
description: Generate JSON-LD structured data (schema.org markup) for an article — Article/BlogPosting, FAQPage, BreadcrumbList, and Organization schemas. Use to add structured data to new or existing articles for rich results in Google.
argument-hint: <slug>
allowed-tools: Bash, Read, Grep, Glob, Write, Edit
---

# Generate Schema

Generate JSON-LD structured data for article: **$ARGUMENTS**

## Phase 1: Gather Article Data

Get the article metadata:

```
seedrank articles schema $ARGUMENTS --json
```

This generates the base Article/BlogPosting + BreadcrumbList + Organization schema from the database and config.

Read the actual article file to detect additional schema opportunities:

```
ls content/**/$ARGUMENTS.mdx 2>/dev/null || ls content/**/$ARGUMENTS.md 2>/dev/null
```

Read the config for product info:

```
cat seedrank.config.yaml
```

## Phase 2: Detect Schema Opportunities

Scan the article content for these patterns:

### FAQPage Schema
Look for an FAQ section (H2 or H3 containing "FAQ", "Frequently Asked", or "Common Questions"). If found, extract each Q&A pair and generate FAQPage schema:

```json
{
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "The question text?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "The answer text."
      }
    }
  ]
}
```

### HowTo Schema
Look for step-by-step instructions (ordered lists under a "How to" heading). If found, generate HowTo schema with named steps.

### Comparison Table Enhancement
If the article has comparison tables, ensure the Article schema includes a `description` field that summarizes what's being compared — this helps Google understand the content for rich snippets.

## Phase 3: Assemble Final Schema

Combine all detected schemas into a single `@graph`:

```json
{
  "@context": "https://schema.org",
  "@graph": [
    { "@type": "BlogPosting", ... },
    { "@type": "BreadcrumbList", ... },
    { "@type": "Organization", ... },
    { "@type": "FAQPage", ... }
  ]
}
```

### Schema Rules
- Only include schema types that match actual content on the page
- Every property must accurately reflect the article content
- Use JSON-LD format (not Microdata or RDFa)
- `datePublished` and `dateModified` must be real dates from the database
- `headline` must match the actual H1 / article title
- FAQ answers should be concise (under 300 chars for rich result eligibility)

## Phase 4: Output Schema

Present the generated JSON-LD in two formats:

### 1. Raw JSON-LD
The complete `@graph` object for copy-paste.

### 2. HTML Script Tag
Ready to drop into the article's `<head>` or frontmatter:

```html
<script type="application/ld+json">
{the json here}
</script>
```

### 3. Integration Suggestion
Based on the article file format:
- **MDX files**: Suggest adding to frontmatter or as a component
- **MD files**: Suggest where to place the script tag
- **If the site uses Next.js or similar**: Note that the schema should go in the page's `<Head>` component

## Output

When done, provide:
1. **Schema types generated**: which types and why
2. **The complete JSON-LD** ready for use
3. **FAQ questions extracted** (if any)
4. **Validation notes**: any potential issues with the schema
5. **Next step**: how to add the schema to the article/site
