"""Google Search Console API client."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

TOKEN_FILE = "token.json"


def normalize_url(url: str) -> str:
    """Normalize a URL for matching: strip protocol, www, trailing slash, query params, fragment.

    Examples:
        https://www.example.com/blog/foo/ -> example.com/blog/foo
        http://example.com/blog/foo?ref=1  -> example.com/blog/foo
        https://example.com/blog/foo#top   -> example.com/blog/foo
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    # Strip www.
    if host.startswith("www."):
        host = host[4:]
    # Path without trailing slash
    path = parsed.path.rstrip("/")
    return f"{host}{path}"


def match_url_to_slug(
    page_url: str,
    articles: list[dict[str, str]],
) -> str | None:
    """Match a GSC page URL to an article slug.

    Tries in order:
    1. Exact match on the stored article URL
    2. Normalized URL match (strips protocol, www, trailing slash, query params)
    3. Path-based match (slug appears at the end of the URL path)

    Args:
        page_url: The URL from GSC data
        articles: List of dicts with 'slug' and 'url' keys

    Returns:
        The matched slug, or None if no match
    """
    # Exact match
    for article in articles:
        if article["url"] and article["url"] == page_url:
            return article["slug"]

    # Normalized match
    normalized_page = normalize_url(page_url)
    for article in articles:
        if article["url"] and normalize_url(article["url"]) == normalized_page:
            return article["slug"]

    # Path-based fallback: check if the article slug appears at the end of the URL path
    parsed = urlparse(page_url)
    path_segments = [s for s in parsed.path.split("/") if s]
    if path_segments:
        last_segment = path_segments[-1]
        for article in articles:
            if article["slug"] == last_segment:
                return article["slug"]

    return None


def authenticate(credentials_path: Path) -> None:
    """Run OAuth flow for Google Search Console."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]

    token_path = credentials_path.parent / TOKEN_FILE
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)
        if creds and creds.valid:
            return

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
    creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json(), encoding="utf-8")


class GSCClient:
    """Client for Google Search Console API."""

    def __init__(self, property_url: str, credentials_path: Path) -> None:
        self.property_url = property_url
        self.credentials_path = credentials_path
        self._service: Any = None

    def _get_service(self) -> Any:
        """Initialize the GSC API service."""
        if self._service:
            return self._service

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
        token_path = self.credentials_path.parent / TOKEN_FILE

        if not token_path.exists():
            raise RuntimeError("Not authenticated. Run 'seedrank gsc auth' first.")

        creds = Credentials.from_authorized_user_file(str(token_path), scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request

                creds.refresh(Request())
                token_path.write_text(creds.to_json(), encoding="utf-8")
            else:
                raise RuntimeError("GSC credentials expired. Run 'seedrank gsc auth' again.")

        self._service = build("searchconsole", "v1", credentials=creds)
        return self._service

    def get_page_performance(self, days: int = 30) -> list[dict[str, Any]]:
        """Fetch page-level performance data from GSC."""
        service = self._get_service()
        end_date = date.today() - timedelta(days=3)  # GSC data lags ~3 days
        start_date = end_date - timedelta(days=days)

        request = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": ["page", "date"],
            "rowLimit": 25000,
        }

        response = (
            service.searchanalytics().query(siteUrl=self.property_url, body=request).execute()
        )

        rows = []
        for row in response.get("rows", []):
            keys = row.get("keys", [])
            rows.append(
                {
                    "page": keys[0] if len(keys) > 0 else "",
                    "date": keys[1] if len(keys) > 1 else "",
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "ctr": row.get("ctr", 0),
                    "position": row.get("position", 0),
                }
            )

        return rows
