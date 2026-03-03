"""GEO (Generative Engine Optimization) query client."""

from __future__ import annotations

import os
import re
from typing import Any

from seedrank.config.schema import AIModelConfig


class GEOClient:
    """Routes queries to different AI model providers and analyzes responses."""

    def __init__(
        self,
        models: list[AIModelConfig],
        brand_name: str,
        competitor_names: list[str] | None = None,
    ) -> None:
        self.models = models
        self.brand_name = brand_name
        self.competitor_names = competitor_names or []

    def query(self, query_text: str, model_config: AIModelConfig) -> dict[str, Any]:
        """Send a query to an AI model and analyze the response."""
        response_text = self._send_query(query_text, model_config)
        analysis = self._analyze_response(response_text)
        return {"response_text": response_text, **analysis}

    def _send_query(self, query_text: str, model_config: AIModelConfig) -> str:
        """Route query to the appropriate provider."""
        api_key = os.environ.get(model_config.api_key_env, "")
        if not api_key:
            raise ValueError(f"API key not found in env var: {model_config.api_key_env}")

        provider = model_config.provider

        if provider in ("openai", "perplexity"):
            return self._query_openai(query_text, model_config, api_key)
        elif provider == "anthropic":
            return self._query_anthropic(query_text, model_config, api_key)
        elif provider == "gemini":
            return self._query_gemini(query_text, model_config, api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _query_openai(self, query: str, config: AIModelConfig, api_key: str) -> str:
        """Query using OpenAI SDK (works for OpenAI and Perplexity)."""
        import openai

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if config.endpoint:
            client_kwargs["base_url"] = config.endpoint

        client = openai.OpenAI(**client_kwargs, max_retries=3)
        response = client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": query}],
            max_tokens=1024,
        )
        return response.choices[0].message.content or ""

    def _query_anthropic(self, query: str, config: AIModelConfig, api_key: str) -> str:
        """Query using Anthropic SDK."""
        import anthropic

        client = anthropic.Anthropic(api_key=api_key, max_retries=3)
        response = client.messages.create(
            model=config.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": query}],
        )
        return response.content[0].text if response.content else ""

    def _query_gemini(self, query: str, config: AIModelConfig, api_key: str) -> str:
        """Query Gemini via REST API with retry."""
        import httpx

        from seedrank.utils.retry import with_retry

        endpoint = (
            config.endpoint
            or f"https://generativelanguage.googleapis.com/v1beta/models/{config.model}:generateContent"
        )

        def _do_request() -> dict:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    endpoint,
                    params={"key": api_key},
                    json={"contents": [{"parts": [{"text": query}]}]},
                )
                resp.raise_for_status()
                return resp.json()

        data = with_retry(_do_request)

        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            return parts[0].get("text", "") if parts else ""
        return ""

    # Sentiment word lists
    _POSITIVE_WORDS = {
        "recommended", "popular", "excellent", "great", "best",
        "leading", "top", "powerful", "reliable", "impressive",
        "innovative", "outstanding", "efficient", "intuitive",
        "versatile", "robust", "seamless", "superior",
    }
    _NEGATIVE_WORDS = {
        "not recommended", "avoid", "issues", "problems", "drawback",
        "lacking", "limited", "poor", "slow", "expensive",
        "complicated", "difficult", "confusing", "outdated",
        "unreliable", "clunky", "disappointing", "frustrating",
    }
    _NEGATION_WORDS = {"not", "no", "never", "neither", "hardly", "barely", "doesn't", "isn't"}
    _SENTIMENT_WINDOW = 150  # characters around brand mention to check

    def _analyze_response(self, text: str) -> dict[str, Any]:
        """Analyze response for brand mentions, sentiment, and citations.

        Uses window-based sentiment: looks at text within _SENTIMENT_WINDOW chars
        of each brand mention, handles negation (e.g., "not great" flips positive
        to negative), and returns a confidence score.
        """
        text_lower = text.lower()
        brand_lower = self.brand_name.lower()

        # Find all brand mention positions
        brand_positions = []
        start = 0
        while True:
            pos = text_lower.find(brand_lower, start)
            if pos == -1:
                break
            brand_positions.append(pos)
            start = pos + 1

        mentions_brand = len(brand_positions)

        # Window-based sentiment around brand mentions
        brand_sentiment = None
        sentiment_confidence = 0.0
        if mentions_brand > 0:
            total_pos = 0
            total_neg = 0
            for bp in brand_positions:
                window_start = max(0, bp - self._SENTIMENT_WINDOW)
                window_end = min(len(text_lower), bp + len(brand_lower) + self._SENTIMENT_WINDOW)
                window = text_lower[window_start:window_end]

                for word in self._POSITIVE_WORDS:
                    if word in window:
                        # Check for negation before the positive word
                        word_pos = window.find(word)
                        prefix = window[max(0, word_pos - 15):word_pos]
                        if any(neg in prefix for neg in self._NEGATION_WORDS):
                            total_neg += 1  # Negated positive → negative
                        else:
                            total_pos += 1

                for word in self._NEGATIVE_WORDS:
                    if word in window:
                        word_pos = window.find(word)
                        prefix = window[max(0, word_pos - 15):word_pos]
                        if any(neg in prefix for neg in self._NEGATION_WORDS):
                            total_pos += 1  # Negated negative → positive
                        else:
                            total_neg += 1

            total_signals = total_pos + total_neg
            if total_signals > 0:
                sentiment_confidence = abs(total_pos - total_neg) / total_signals
                if total_pos > total_neg:
                    brand_sentiment = "positive"
                elif total_neg > total_pos:
                    brand_sentiment = "negative"
                else:
                    brand_sentiment = "neutral"
            else:
                brand_sentiment = "neutral"
                sentiment_confidence = 0.0

        # Extract URLs/citations
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        citations = list(set(re.findall(url_pattern, text)))

        # Detect competitor mentions
        mentions_competitors: list[str] = [
            name for name in self.competitor_names
            if name.lower() in text_lower
        ]

        return {
            "mentions_brand": mentions_brand,
            "brand_sentiment": brand_sentiment,
            "sentiment_confidence": sentiment_confidence,
            "mentions_competitors": mentions_competitors,
            "citations": citations,
        }
