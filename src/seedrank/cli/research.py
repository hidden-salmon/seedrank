"""seedrank research — Keyword research and SERP analysis commands."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from seedrank.utils.console import error, heading, info, success

research_app = typer.Typer(
    help="Research commands — keywords, SERP, competitors, GEO.", no_args_is_help=True
)


def _staleness_days(workspace: Path) -> int:
    """Load data_staleness_days from config, default 90."""
    try:
        from seedrank.config.loader import load_config

        cfg = load_config(workspace / "seedrank.config.yaml")
        return cfg.legal.data_staleness_days
    except Exception:
        return 90


@research_app.command(name="keywords")
def research_keywords(
    keywords: str = typer.Argument(help="Comma-separated keywords to research."),
    location: int = typer.Option(
        2840, "--location", "-l", help="DataForSEO location code (2840=US)."
    ),
    language: str = typer.Option("en", "--language", help="Language code."),
    expand: bool = typer.Option(False, "--expand", help="Also fetch keyword suggestions."),
    force: bool = typer.Option(
        False, "--force", "-f", help="Bypass cache and fetch fresh data."
    ),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Fetch keyword data from DataForSEO and store in database."""
    heading("Research Keywords")

    from seedrank.config.loader import load_config
    from seedrank.data.db import connect, get_db_path
    from seedrank.research.dataforseo import DataForSEOClient

    try:
        cfg = load_config(workspace / "seedrank.config.yaml")
    except (FileNotFoundError, ValueError) as e:
        error(str(e))
        raise typer.Exit(1)

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    if not keyword_list:
        error("No keywords provided.")
        raise typer.Exit(1)

    # Cache-first: check for fresh data
    to_fetch = keyword_list
    if not force:
        from seedrank.data.cache import get_fresh_keywords

        max_age = cfg.legal.data_staleness_days
        with connect(db_path) as conn:
            stale, cached = get_fresh_keywords(conn, keyword_list, max_age)

        if cached:
            info(
                f"Cache: {len(cached)} keyword(s) already fresh"
                f" (<{max_age}d old)"
            )
        if not stale:
            success(
                "All keywords have fresh data. Use --force to re-fetch."
            )
            return
        to_fetch = stale
        if len(to_fetch) < len(keyword_list):
            info(f"Fetching {len(to_fetch)} stale/missing keyword(s)...")

    info(f"Researching {len(to_fetch)} keyword(s)...")

    client = DataForSEOClient(cfg.dataforseo)
    results = client.fetch_keyword_overview(
        to_fetch, location=location, language=language
    )

    with connect(db_path) as conn:
        from seedrank.data.costs import log_api_cost

        log_api_cost(
            conn,
            provider="dataforseo",
            endpoint="keywords_data/google_ads/search_volume/live",
            context=f"keywords: {len(to_fetch)}",
        )
        for kw_data in results:
            conn.execute(
                """INSERT OR REPLACE INTO keywords
                   (keyword, volume, kd, cpc, competition, intent,
                    serp_features, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (
                    kw_data["keyword"],
                    kw_data.get("volume"),
                    kw_data.get("kd"),
                    kw_data.get("cpc"),
                    kw_data.get("competition"),
                    kw_data.get("intent"),
                    json.dumps(kw_data.get("serp_features", [])),
                ),
            )

    success(f"Stored {len(results)} keyword(s) in database.")

    if expand:
        info("Fetching keyword suggestions...")
        for seed in keyword_list:
            suggestions = client.fetch_keyword_suggestions(
                seed, location=location, language=language
            )
            with connect(db_path) as conn:
                for kw_data in suggestions:
                    conn.execute(
                        """INSERT OR IGNORE INTO keywords
                           (keyword, volume, kd, cpc, competition,
                            intent, serp_features, fetched_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                        (
                            kw_data["keyword"],
                            kw_data.get("volume"),
                            kw_data.get("kd"),
                            kw_data.get("cpc"),
                            kw_data.get("competition"),
                            kw_data.get("intent"),
                            json.dumps(kw_data.get("serp_features", [])),
                        ),
                    )
            success(f"  Added {len(suggestions)} suggestions for '{seed}'")


@research_app.command(name="serp")
def research_serp(
    keyword: str = typer.Argument(help="Keyword to get SERP snapshot for."),
    location: int = typer.Option(
        2840, "--location", "-l", help="DataForSEO location code."
    ),
    language: str = typer.Option("en", "--language", help="Language code."),
    force: bool = typer.Option(
        False, "--force", "-f", help="Bypass cache and fetch fresh data."
    ),
    workspace: Path = typer.Option(
        Path("."), "--workspace", "-w", help="Workspace root."
    ),
) -> None:
    """Fetch SERP snapshot for a keyword from DataForSEO."""
    heading("Research SERP")

    from seedrank.config.loader import load_config
    from seedrank.data.db import connect, get_db_path
    from seedrank.research.dataforseo import DataForSEOClient

    try:
        cfg = load_config(workspace / "seedrank.config.yaml")
    except (FileNotFoundError, ValueError) as e:
        error(str(e))
        raise typer.Exit(1)

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    # Cache-first: check for fresh SERP data
    if not force:
        from seedrank.data.cache import get_fresh_serp

        max_age = cfg.legal.data_staleness_days
        with connect(db_path) as conn:
            cached = get_fresh_serp(conn, keyword, max_age)
        if cached:
            success(
                f"Cache: SERP for '{keyword}' is fresh"
                f" ({len(cached)} results, <{max_age}d old)."
                " Use --force to re-fetch."
            )
            return

    info(f"Fetching SERP for '{keyword}'...")
    client = DataForSEOClient(cfg.dataforseo)
    results = client.fetch_serp(keyword, location=location, language=language)

    with connect(db_path) as conn:
        from seedrank.data.costs import log_api_cost

        log_api_cost(
            conn,
            provider="dataforseo",
            endpoint="serp/google/organic/live/advanced",
            context=f"serp: {keyword}",
        )
        for item in results:
            conn.execute(
                """INSERT INTO serp_snapshots
                   (keyword, rank, url, domain, title, snippet,
                    result_type, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (
                    keyword,
                    item["rank"],
                    item.get("url"),
                    item.get("domain"),
                    item.get("title"),
                    item.get("snippet"),
                    item.get("result_type", "organic"),
                ),
            )

    success(f"Stored {len(results)} SERP results for '{keyword}'.")


@research_app.command(name="competitors")
def research_competitors(
    domain: str = typer.Argument(help="Competitor domain to research."),
    slug: str = typer.Option(
        "", "--slug", "-s",
        help="Competitor slug (defaults to domain minus TLD).",
    ),
    limit: int = typer.Option(
        100, "--limit", "-n", help="Max keywords to fetch."
    ),
    location: int = typer.Option(
        2840, "--location", "-l", help="DataForSEO location code."
    ),
    language: str = typer.Option("en", "--language", help="Language code."),
    force: bool = typer.Option(
        False, "--force", "-f", help="Bypass cache and fetch fresh data."
    ),
    workspace: Path = typer.Option(
        Path("."), "--workspace", "-w", help="Workspace root."
    ),
) -> None:
    """Fetch competitor keyword rankings from DataForSEO."""
    heading("Research Competitors")

    from seedrank.config.loader import load_config
    from seedrank.data.db import connect, get_db_path
    from seedrank.research.dataforseo import DataForSEOClient

    try:
        cfg = load_config(workspace / "seedrank.config.yaml")
    except (FileNotFoundError, ValueError) as e:
        error(str(e))
        raise typer.Exit(1)

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    comp_slug = slug or domain.split(".")[0]

    # Cache-first: check for fresh competitor data
    if not force:
        from seedrank.data.cache import get_fresh_competitor_keywords

        max_age = cfg.legal.data_staleness_days
        with connect(db_path) as conn:
            cached = get_fresh_competitor_keywords(conn, comp_slug, max_age)
        if cached:
            success(
                f"Cache: {len(cached)} keywords for '{comp_slug}'"
                f" are fresh (<{max_age}d old)."
                " Use --force to re-fetch."
            )
            return

    info(f"Fetching keywords for {domain} (slug: {comp_slug})...")

    client = DataForSEOClient(cfg.dataforseo)
    results = client.fetch_competitor_keywords(
        domain, location=location, language=language, limit=limit
    )

    with connect(db_path) as conn:
        from seedrank.data.costs import log_api_cost

        log_api_cost(
            conn,
            provider="dataforseo",
            endpoint="dataforseo_labs/google/ranked_keywords/live",
            context=f"competitors: {domain}",
        )
        for kw_data in results:
            conn.execute(
                """INSERT OR REPLACE INTO competitor_keywords
                   (competitor_slug, keyword, rank, url, volume, kd,
                    fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
                (
                    comp_slug,
                    kw_data["keyword"],
                    kw_data.get("rank"),
                    kw_data.get("url"),
                    kw_data.get("volume"),
                    kw_data.get("kd"),
                ),
            )

    success(f"Stored {len(results)} keywords for {domain}.")


@research_app.command(name="expand")
def research_expand(
    keyword: str = typer.Argument(help="Seed keyword to expand."),
    location: int = typer.Option(
        2840, "--location", "-l", help="DataForSEO location code."
    ),
    language: str = typer.Option("en", "--language", help="Language code."),
    workspace: Path = typer.Option(
        Path("."), "--workspace", "-w", help="Workspace root."
    ),
) -> None:
    """Get keyword suggestions for a seed keyword."""
    heading("Expand Keywords")

    from seedrank.config.loader import load_config
    from seedrank.data.db import connect, get_db_path
    from seedrank.research.dataforseo import DataForSEOClient

    try:
        cfg = load_config(workspace / "seedrank.config.yaml")
    except (FileNotFoundError, ValueError) as e:
        error(str(e))
        raise typer.Exit(1)

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    info(f"Expanding '{keyword}'...")
    client = DataForSEOClient(cfg.dataforseo)
    results = client.fetch_keyword_suggestions(
        keyword, location=location, language=language
    )

    with connect(db_path) as conn:
        from seedrank.data.costs import log_api_cost

        log_api_cost(
            conn,
            provider="dataforseo",
            endpoint="dataforseo_labs/google/keyword_suggestions/live",
            context=f"expand: {keyword}",
        )
        for kw_data in results:
            conn.execute(
                """INSERT OR IGNORE INTO keywords
                   (keyword, volume, kd, cpc, competition, intent,
                    serp_features, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (
                    kw_data["keyword"],
                    kw_data.get("volume"),
                    kw_data.get("kd"),
                    kw_data.get("cpc"),
                    kw_data.get("competition"),
                    kw_data.get("intent"),
                    json.dumps(kw_data.get("serp_features", [])),
                ),
            )

    success(f"Added {len(results)} keyword suggestions.")


@research_app.command(name="questions")
def research_questions(
    query: str = typer.Argument(
        help="Search query to find related questions."
    ),
    provider: str = typer.Option(
        "perplexity", "--provider", "-p",
        help="AI provider: perplexity, chatgpt.",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Bypass cache and fetch fresh data."
    ),
    workspace: Path = typer.Option(
        Path("."), "--workspace", "-w", help="Workspace root."
    ),
) -> None:
    """Discover questions developers ask about a topic.

    Fetches PAA from Google SERP + AI model responses. Stores unique
    questions in the questions table for assignment to articles.
    """
    heading("Research Questions")

    from seedrank.config.loader import load_config
    from seedrank.data.db import connect, get_db_path
    from seedrank.research.dataforseo import DataForSEOClient

    try:
        cfg = load_config(workspace / "seedrank.config.yaml")
    except (FileNotFoundError, ValueError) as e:
        error(str(e))
        raise typer.Exit(1)

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    # Ensure questions table exists (run migrations)
    from seedrank.data.migrations import migrate_db

    with connect(db_path) as conn:
        migrate_db(conn)

    # Cache-first: check for fresh questions
    if not force:
        from seedrank.data.cache import get_fresh_questions

        max_age = cfg.legal.data_staleness_days
        with connect(db_path) as conn:
            cached = get_fresh_questions(conn, query, max_age)
        if cached:
            success(
                f"Cache: {len(cached)} questions for '{query}' are"
                f" fresh (<{max_age}d old). Use --force to re-fetch."
            )
            return

    client = DataForSEOClient(cfg.dataforseo)
    all_questions: list[dict] = []

    # Step 1: Fetch SERP PAA
    info(f"Fetching PAA for '{query}'...")
    try:
        serp_result = client.fetch_serp_paa(query)
        paa_questions = serp_result.get("paa", [])
        for pq in paa_questions:
            if pq.get("question"):
                all_questions.append({
                    "question": pq["question"],
                    "source": "paa",
                    "source_keyword": query,
                })
        info(f"  Found {len(paa_questions)} PAA questions")
    except Exception as e:
        error(f"  SERP PAA failed: {e}")

    # Step 2: Fetch AI responses
    info(f"Fetching {provider} response for '{query}'...")
    try:
        ai_result = client.fetch_ai_responses(query, provider=provider)
        response_text = ai_result.get("response_text", "")
        # Extract questions from the AI response (lines ending with ?)
        import re

        ai_questions = re.findall(r"([^\n.?!]*\?)", response_text)
        for aq in ai_questions:
            cleaned = aq.strip().lstrip("- *#>0123456789.")
            if len(cleaned) > 15:  # Skip very short fragments
                all_questions.append({
                    "question": cleaned.strip(),
                    "source": provider,
                    "source_keyword": query,
                })
        info(
            f"  Extracted {len(ai_questions)} questions"
            f" from {provider} response"
        )
    except Exception as e:
        error(f"  AI response failed: {e}")

    # Step 3: Deduplicate and store
    with connect(db_path) as conn:
        from seedrank.data.costs import log_api_cost

        log_api_cost(
            conn,
            provider="dataforseo",
            endpoint="serp+ai_responses",
            context=f"questions: {query}",
        )

        inserted = 0
        for q in all_questions:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO questions
                       (question, source, source_keyword, fetched_at)
                       VALUES (?, ?, ?, datetime('now'))""",
                    (q["question"], q["source"], q["source_keyword"]),
                )
                if conn.total_changes:
                    inserted += 1
            except Exception:
                pass  # Ignore duplicates

        conn.commit()

    success(
        f"Stored {inserted} new question(s)"
        f" from {len(all_questions)} discovered."
    )


@research_app.command(name="geo")
def research_geo(
    queries_file: Path = typer.Argument(
        help="YAML file with queries to run across AI models."
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Bypass cache and re-query all models.",
    ),
    workspace: Path = typer.Option(
        Path("."), "--workspace", "-w", help="Workspace root."
    ),
) -> None:
    """Run GEO queries across AI models and store results."""
    heading("GEO Research")

    from seedrank.config.loader import load_config
    from seedrank.data.db import connect, get_db_path
    from seedrank.research.geo import GEOClient

    try:
        cfg = load_config(workspace / "seedrank.config.yaml")
    except (FileNotFoundError, ValueError) as e:
        error(str(e))
        raise typer.Exit(1)

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    if not queries_file.exists():
        error(f"Queries file not found: {queries_file}")
        raise typer.Exit(1)

    import yaml

    queries = yaml.safe_load(queries_file.read_text(encoding="utf-8"))
    if not isinstance(queries, list):
        error("Queries file must be a YAML list of strings.")
        raise typer.Exit(1)

    if not cfg.ai_models:
        error("No AI models configured in seedrank.config.yaml.")
        raise typer.Exit(1)

    competitor_names = [c.name for c in cfg.competitors]
    geo_client = GEOClient(
        cfg.ai_models, cfg.product.name, competitor_names
    )

    total = 0
    skipped = 0
    for query in queries:
        info(f"Query: {query}")
        for model_cfg in cfg.ai_models:
            # Cache-first: check for recent GEO result
            if not force:
                from seedrank.data.cache import get_fresh_geo_queries

                with connect(db_path) as conn:
                    cached = get_fresh_geo_queries(
                        conn, query, model_cfg.slug, max_age_days=7
                    )
                if cached:
                    r = cached[0]
                    status = (
                        "mentioned"
                        if r.get("mentions_brand")
                        else "not mentioned"
                    )
                    info(f"  {model_cfg.slug}: {status} (cached)")
                    skipped += 1
                    continue

            try:
                result = geo_client.query(query, model_cfg)
                with connect(db_path) as conn:
                    from seedrank.data.costs import log_api_cost

                    log_api_cost(
                        conn,
                        provider=model_cfg.provider,
                        endpoint=model_cfg.model,
                        context=f"geo: {query[:50]}",
                    )
                    conn.execute(
                        """INSERT INTO geo_queries
                           (query, model, response_text, mentions_brand,
                            brand_sentiment, mentions_competitors,
                            citations, queried_at)
                           VALUES
                           (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                        (
                            query,
                            model_cfg.slug,
                            result["response_text"],
                            result.get("mentions_brand", 0),
                            result.get("brand_sentiment"),
                            json.dumps(
                                result.get("mentions_competitors", [])
                            ),
                            json.dumps(result.get("citations", [])),
                        ),
                    )
                total += 1
                status = (
                    "mentioned"
                    if result.get("mentions_brand")
                    else "not mentioned"
                )
                info(f"  {model_cfg.slug}: {status}")
            except Exception as e:
                error(f"  {model_cfg.slug}: failed — {e}")

    msg = f"Completed {total} GEO queries."
    if skipped:
        msg += f" Skipped {skipped} cached."
    success(msg)
