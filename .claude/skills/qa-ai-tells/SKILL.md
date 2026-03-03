---
name: qa-ai-tells
description: "Detect AI writing tells — tricolons, crutch phrases, diplomatic hedging, meta-commentary, and other patterns that make content read as machine-generated. Run after writing, before review."
argument-hint: <path-to-article>
allowed-tools: Bash, Read, Grep, Glob, Edit
---

# QA: AI-Tell Detection

Scan this article for AI writing patterns that erode reader trust: **$ARGUMENTS**

This is not about factual accuracy or legal compliance (those are covered by `/review-article` and `/audit-legal`). This is about catching the subtle tells that make content *feel* AI-generated to experienced readers — even when the facts are correct.

## Step 1: Run automated detection

```
seedrank validate article $ARGUMENTS --json
```

Parse the JSON output. Look specifically for issues with check names starting with `ai_tell_`. These are the automated detections.

## Step 2: Read the full article

Read the article end to end. The automated checks catch patterns; this manual pass catches context-dependent tells that regex cannot.

## Check 1: Tricolons

Look for three parallel short sentences with identical grammatical structure.

Examples of the pattern:
- "X is smaller. Y is clearer. Z is simpler."
- "It handles routing. It manages state. It scales effortlessly."
- "Speed matters. Reliability matters. Cost matters."

Two in a row is fine for emphasis. Three with the same structure is an AI tell. Vary sentence length — make one long, one short, one medium.

**Fix**: Rewrite to vary sentence length and structure. Combine two of the three into one sentence, or break the symmetry.

## Check 2: AI crutch phrases

These phrases appear disproportionately in AI-generated content. Flag every instance:

- "Here's [topic]" / "Here's what you need to know"
- "worth noting" / "it's worth noting"
- "Whether you need X, Y, or Z"
- "Let's dive in" / "let's break it down"
- "In today's [landscape/world/market]"
- "stands out" / "really shines"
- "when it comes to"
- "at the end of the day"
- "it's important to note"
- "the bottom line"
- "in a nutshell"

Note: The `voice.banned_words` list in the config catches product-specific banned words. This check catches structural AI phrases that are product-agnostic.

**Fix**: Delete the phrase and start with the actual point. "It's worth noting that deploys take 30 seconds" becomes "Deploys take 30 seconds."

## Check 3: Excessive date stamps

Count instances of "(as of [Month] [Year])" or similar date patterns. Having dated facts is good (it is a citability signal), but AI tends to stamp every single claim.

- 1-3 per article: fine
- 4-6 per article: borderline, consolidate into a header note
- 7+: excessive, add a single "All data as of [Month Year]" note at the top and remove inline stamps except on the most critical claims

**Fix**: Add a "Data last verified: [Month Year]" note near the top. Keep inline dates only on pricing and the most important competitor claims.

## Check 4: Self-announcing honesty

Phrases that tell the reader you are being honest (which implies you might not be otherwise):

- "verified pricing"
- "honest trade-offs" / "the honest answer"
- "we honestly think"
- "to be frank" / "frankly"
- "the truth is"
- "in all honesty"
- "let me be real"

**Fix**: Delete. Just state the fact. If the pricing is verified, the "(as of [date])" and source link prove it — you do not need to announce it.

## Check 5: Meta-commentary

Sentences about the article's own structure instead of the actual content:

- "This is the section that matters most"
- "This guide breaks down..."
- "In this section, we'll cover..."
- "Now let's move on to..."
- "As mentioned earlier..."
- "As we discussed above..."
- "We've covered X, now let's look at Y"

Note: C4 (answer-first structure) catches filler after H2s. This check catches meta-commentary anywhere in the article body.

**Fix**: Delete the meta-commentary. If the reader needs orientation, the heading already provides it.

## Check 6: Perfect symmetry

Read the article's structure as a whole. Flag if:

- Every H2 section has the same approximate word count (within 20%)
- Every bulleted list has the same number of items
- Every FAQ answer is the same length (within 2 sentences)
- Every comparison follows an identical sentence template

Real articles have natural variation. A 200-word section followed by a 500-word section followed by a 150-word section feels human. Five 300-word sections in a row feels generated.

**Fix**: Vary section lengths. Expand the sections that deserve more depth. Trim the ones that do not. Some FAQ answers should be one sentence; others should be a paragraph.

## Check 7: FAQ body repetition

For each FAQ answer, check whether it substantially repeats content from earlier in the article. AI models often generate FAQ sections by rephrasing their own prior output.

Compare each FAQ answer against the article body. If >60% of a FAQ answer's content appears (even paraphrased) in the body, it adds no value.

**Fix**: FAQ answers should add new information or provide a more direct/condensed answer than the body. If the article body says "AZIN costs $5/month for the starter tier with 3 services and 1GB RAM per service," the FAQ answer to "How much does AZIN cost?" should not repeat that verbatim — it should add context: "Starts at $5/month. See the pricing comparison table above for a full breakdown against alternatives."

## Check 8: Missing editorial voice

Read the full article and check whether it ever takes a genuine stance:

- Does it make a clear recommendation?
- Does it say "we think X is better for Y because Z"?
- Does it have a paragraph that could not have been written by a different product's marketing team?

If every sentence is hedged and interchangeable, the article has no voice. Readers (and AI models) prefer content with a clear perspective.

**Fix**: Add 2-3 opinionated statements. Not sales copy — genuine technical opinions. "We think Fly.io's approach to multi-region is elegant but overcomplicates single-region deploys" is a real opinion. "Both platforms have their strengths" is not.

## Check 9: Gratuitous competitor compliments

The AI praise-then-pivot pattern:

- "[Competitor] is an impressive project, but..."
- "[Competitor] has done remarkable work in..."
- "[Competitor] is a solid choice, however..."
- "We have great respect for [Competitor]..."
- "[Competitor] is a fantastic option for..."

Real competitive content acknowledges competitor strengths matter-of-factly without performative praise.

**Fix**: State the fact without the compliment. "Railway has a generous free tier" is fine. "Railway is an impressive platform with a generous free tier" is AI padding.

## Check 10: Counting before listing

Announcing how many items are in a list before listing them:

- "Three things matter here:"
- "There are four key differences:"
- "Five forces drive this decision:"
- "Two main factors to consider:"

Just list them. The reader can count.

**Fix**: Remove the count. Start with the first item.

## Check 11: Over-explaining obvious concepts

Content that explains basic concepts to an audience that already knows them. This is audience-dependent — check the config's persona definitions.

For a senior developer audience, do not explain:
- What a container is
- What CI/CD stands for
- What a REST API is
- What environment variables are
- Basic Git concepts

For a beginner audience, these explanations may be appropriate.

**Fix**: Delete the explanation or compress it to a parenthetical. "Environment variables (the standard way to pass config to containers)" is fine for mid-level. A full paragraph explaining env vars to senior devs is not.

## Check 12: Balanced diplomatic hedging

Phrases that avoid taking any position:

- "Neither is universally better"
- "None of these are deal-breakers"
- "It depends on your specific needs"
- "Both have their pros and cons"
- "The best choice depends on your requirements"
- "There's no one-size-fits-all answer"
- "Each has its own strengths"
- "Your mileage may vary"

One hedge per article is fine — sometimes it genuinely depends. Multiple hedges signal AI-generated fence-sitting.

**Fix**: Replace with a specific recommendation. "It depends on your needs" becomes "If you need multi-region, choose X. If you need lower cost, choose Y."

## Output: Structured Report

Produce a structured report:

### Verdict: CLEAN / NEEDS EDITING / REWRITE

- **CLEAN**: 0-2 minor tells found. Publish as-is.
- **NEEDS EDITING**: 3-8 tells found. Fixable with targeted edits.
- **REWRITE**: 9+ tells or pervasive structural issues (perfect symmetry + missing voice + FAQ repetition). The article reads as AI-generated.

### AI-Tell Summary
| # | Check | Instances | Severity |
|---|-------|-----------|----------|
| 1 | Tricolons | 0 | - |
| 2 | Crutch phrases | 2 | minor |
| ... | ... | ... | ... |

### Instances Found
For each detected tell:
- **Check**: Which check
- **Location**: Heading or line reference
- **Text**: Exact quote
- **Fix**: Specific rewrite suggestion

### Overall Assessment
2-3 sentences on the article's AI-tell posture. Does it read like a human wrote it? Would a developer notice the patterns?

## Important

- This is a writing quality check, not a factual or legal check. Those are separate skills.
- Do NOT rewrite the article. Flag issues and suggest fixes. The author decides.
- Some patterns are fine in isolation. Flag them when they cluster — three crutch phrases in one article is a problem; one is not.
- The goal is content that reads as if a knowledgeable human wrote it. Not "AI-free" content — content where the AI patterns have been edited out.
- Be specific. "The article feels AI-generated" is useless feedback. "Lines 45-47 are a tricolon, the FAQ repeats the pricing section verbatim, and 'worth noting' appears 4 times" is actionable.
