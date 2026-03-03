"""Retry utility with exponential backoff for HTTP calls."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Retryable HTTP status codes
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def with_retry(
    fn: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple[type[Exception], ...] = (
        httpx.ConnectError,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ),
) -> T:
    """Execute a function with exponential backoff retry.

    Retries on:
    - Network errors (connect, timeout, pool)
    - HTTP 429/5xx status codes (via httpx.HTTPStatusError)

    Args:
        fn: Zero-argument callable to execute.
        max_retries: Maximum number of retry attempts (0 = no retries).
        base_delay: Initial delay in seconds between retries.
        max_delay: Maximum delay cap in seconds.
        retryable_exceptions: Tuple of exception types to retry on.

    Returns:
        The return value of fn().

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return fn()
        except httpx.HTTPStatusError as e:
            if e.response.status_code not in RETRYABLE_STATUS_CODES:
                raise
            last_exception = e
        except retryable_exceptions as e:
            last_exception = e

        if attempt < max_retries:
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(
                "Retry %d/%d after %.1fs: %s",
                attempt + 1,
                max_retries,
                delay,
                last_exception,
            )
            time.sleep(delay)

    raise last_exception  # type: ignore[misc]
