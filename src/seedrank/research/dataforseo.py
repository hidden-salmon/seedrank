"""DataForSEO API client wrapper."""

from __future__ import annotations

import os
from typing import Any

import httpx

from seedrank.config.schema import DataForSeoConfig

DATAFORSEO_BASE = "https://api.dataforseo.com/v3"


class DataForSEOClient:
    """Client for DataForSEO REST API."""

    def __init__(self, config: DataForSeoConfig) -> None:
        self.login = config.login or os.environ.get("DATAFORSEO_LOGIN", "")
        self.password = config.password or os.environ.get("DATAFORSEO_PASSWORD", "")
        if not self.login or not self.password:
            raise ValueError(
                "DataForSEO credentials not found. Set "
                "DATAFORSEO_LOGIN/DATAFORSEO_PASSWORD env vars "
                "or configure in seedrank.config.yaml."
            )
        self.default_location = config.location
        self.default_language = config.language

    def _request(self, endpoint: str, data: list[dict]) -> list[dict]:
        """Make authenticated POST request to DataForSEO with retry."""
        from seedrank.utils.retry import with_retry

        def _do_request() -> dict:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{DATAFORSEO_BASE}{endpoint}",
                    json=data,
                    auth=(self.login, self.password),
                )
                resp.raise_for_status()
                return resp.json()

        result = with_retry(_do_request)

        if result.get("status_code") != 20000:
            msg = result.get("status_message", "Unknown error")
            raise RuntimeError(f"DataForSEO error: {msg}")

        return result.get("tasks", [])

    def _extract_results(self, tasks: list[dict]) -> list[dict]:
        """Extract result items from DataForSEO task response."""
        items = []
        for task in tasks:
            if task.get("status_code") != 20000:
                continue
            for result_set in task.get("result", []):
                if result_set and "items" in result_set:
                    items.extend(result_set["items"] or [])
        return items

    def fetch_keyword_overview(
        self,
        keywords: list[str],
        location: int | None = None,
        language: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch keyword overview data (volume, KD, CPC, etc.)."""
        data = [
            {
                "keywords": keywords,
                "location_code": location or self.default_location,
                "language_code": language or self.default_language,
            }
        ]
        tasks = self._request("/keywords_data/google_ads/search_volume/live", data)
        items = self._extract_results(tasks)

        results = []
        for item in items:
            results.append(
                {
                    "keyword": item.get("keyword", ""),
                    "volume": item.get("search_volume"),
                    "kd": item.get("keyword_difficulty"),
                    "cpc": item.get("cpc"),
                    "competition": item.get("competition"),
                    "intent": item.get("search_intent", {}).get("main")
                    if isinstance(item.get("search_intent"), dict)
                    else None,
                    "serp_features": item.get("serp_features", []),
                }
            )
        return results

    def fetch_keyword_suggestions(
        self,
        seed: str,
        location: int | None = None,
        language: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch keyword suggestions for a seed keyword."""
        data = [
            {
                "keyword": seed,
                "location_code": location or self.default_location,
                "language_code": language or self.default_language,
                "limit": 50,
            }
        ]
        tasks = self._request("/dataforseo_labs/google/keyword_suggestions/live", data)
        items = self._extract_results(tasks)

        results = []
        for item in items:
            kw_data = item.get("keyword_data", item)
            ki = kw_data.get("keyword_info", {})
            results.append(
                {
                    "keyword": kw_data.get("keyword", ""),
                    "volume": ki.get("search_volume"),
                    "kd": kw_data.get("keyword_properties", {}).get("keyword_difficulty"),
                    "cpc": ki.get("cpc"),
                    "competition": ki.get("competition"),
                    "intent": None,
                    "serp_features": [],
                }
            )
        return results

    def fetch_serp(
        self,
        keyword: str,
        location: int | None = None,
        language: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch live SERP results for a keyword."""
        data = [
            {
                "keyword": keyword,
                "location_code": location or self.default_location,
                "language_code": language or self.default_language,
            }
        ]
        tasks = self._request("/serp/google/organic/live/advanced", data)
        items = self._extract_results(tasks)

        results = []
        for i, item in enumerate(items, 1):
            results.append(
                {
                    "rank": item.get("rank_group", i),
                    "url": item.get("url"),
                    "domain": item.get("domain"),
                    "title": item.get("title"),
                    "snippet": item.get("description"),
                    "result_type": item.get("type", "organic"),
                }
            )
        return results

    def fetch_serp_paa(
        self,
        keyword: str,
        location: int | None = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Fetch SERP results WITH People Also Ask questions extracted.

        Uses the same /serp/google/organic/live/advanced endpoint but
        parses PAA items from the result.
        Returns: {"organic": [...], "paa": [...], "related_searches": [...]}
        """
        data = [
            {
                "keyword": keyword,
                "location_code": location or self.default_location,
                "language_code": language or self.default_language,
            }
        ]
        tasks = self._request("/serp/google/organic/live/advanced", data)

        organic = []
        paa = []
        related_searches = []

        for task in tasks:
            if task.get("status_code") != 20000:
                continue
            for result_set in task.get("result", []):
                if not result_set:
                    continue
                for item in result_set.get("items", []) or []:
                    item_type = item.get("type", "")
                    if item_type == "people_also_ask":
                        # PAA items contain nested items with questions
                        paa_items = item.get("items", []) or []
                        for paa_item in paa_items:
                            paa.append({
                                "question": paa_item.get("title", ""),
                                "url": paa_item.get("url", ""),
                                "snippet": paa_item.get("description", ""),
                            })
                    elif item_type == "related_searches":
                        rs_items = item.get("items", []) or []
                        for rs_item in rs_items:
                            related_searches.append(rs_item.get("title", ""))
                    elif item_type == "organic":
                        organic.append({
                            "rank": item.get("rank_group", 0),
                            "url": item.get("url"),
                            "domain": item.get("domain"),
                            "title": item.get("title"),
                            "snippet": item.get("description"),
                        })

        return {"organic": organic, "paa": paa, "related_searches": related_searches}

    def fetch_ai_responses(
        self,
        query: str,
        provider: str = "perplexity",
        location: int | None = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Fetch AI model response via DataForSEO AI Optimization API.

        Endpoints:
        - perplexity: /ai_optimization/perplexity/llm_responses/live
        - chatgpt: /ai_optimization/chat_gpt/llm_responses/live

        Returns: {"response_text": str, "citations": [...]}
        """
        provider_paths = {
            "perplexity": "/ai_optimization/perplexity/llm_responses/live",
            "chatgpt": "/ai_optimization/chat_gpt/llm_responses/live",
        }
        endpoint = provider_paths.get(provider)
        if not endpoint:
            raise ValueError(f"Unsupported AI provider: {provider}. Use 'perplexity' or 'chatgpt'.")

        data = [
            {
                "query": query,
                "location_code": location or self.default_location,
                "language_code": language or self.default_language,
            }
        ]
        tasks = self._request(endpoint, data)

        response_text = ""
        citations: list[str] = []

        for task in tasks:
            if task.get("status_code") != 20000:
                continue
            for result_set in task.get("result", []):
                if not result_set:
                    continue
                # Extract the response text
                items = result_set.get("items", []) or []
                for item in items:
                    if item.get("text"):
                        response_text += item["text"] + "\n"
                    if item.get("citations"):
                        citations.extend(item["citations"])
                    # Some responses have response_text at top level
                    if item.get("response_text"):
                        response_text += item["response_text"] + "\n"

        return {"response_text": response_text.strip(), "citations": list(set(citations))}

    def fetch_ai_keyword_volume(
        self,
        keywords: list[str],
        location: int | None = None,
        language: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch AI-specific keyword search volume.

        Endpoint: /ai_optimization/ai_keyword_data/keywords_search_volume/live
        Returns: [{"keyword": str, "ai_volume": int, "trend": str}, ...]
        """
        data = [
            {
                "keywords": keywords,
                "location_code": location or self.default_location,
                "language_code": language or self.default_language,
            }
        ]
        tasks = self._request(
            "/ai_optimization/ai_keyword_data/keywords_search_volume/live", data
        )
        items = self._extract_results(tasks)

        results = []
        for item in items:
            results.append({
                "keyword": item.get("keyword", ""),
                "ai_volume": item.get("search_volume") or item.get("ai_search_volume", 0),
                "trend": item.get("trend", ""),
            })
        return results

    def fetch_competitor_keywords(
        self,
        domain: str,
        location: int | None = None,
        language: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch keywords a competitor domain ranks for."""
        data = [
            {
                "target": domain,
                "location_code": location or self.default_location,
                "language_code": language or self.default_language,
                "limit": limit,
                "order_by": ["keyword_data.keyword_info.search_volume,desc"],
            }
        ]
        tasks = self._request("/dataforseo_labs/google/ranked_keywords/live", data)
        items = self._extract_results(tasks)

        results = []
        for item in items:
            kw_data = item.get("keyword_data", {})
            ki = kw_data.get("keyword_info", {})
            ranked = item.get("ranked_serp_element", {})
            results.append(
                {
                    "keyword": kw_data.get("keyword", ""),
                    "rank": ranked.get("serp_item", {}).get("rank_group"),
                    "url": ranked.get("serp_item", {}).get("url"),
                    "volume": ki.get("search_volume"),
                    "kd": kw_data.get("keyword_properties", {}).get("keyword_difficulty"),
                }
            )
        return results
