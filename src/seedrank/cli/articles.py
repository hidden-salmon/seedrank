"""seedrank articles — Article registration and crosslink management."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from seedrank.utils.console import console, error, heading, info, render_table, success

articles_app = typer.Typer(help="Article management commands.", no_args_is_help=True)


@articles_app.command(name="register")
def articles_register(
    slug: str = typer.Argument(help="Article slug (URL-friendly identifier)."),
    title: str = typer.Option(..., "--title", "-t", help="Article title."),
    keywords: str = typer.Option("", "--keywords", "-k", help="Comma-separated target keywords."),
    topics: str = typer.Option("", "--topics", help="Comma-separated topics."),
    content_type: str = typer.Option("blog", "--type", help="Content type slug."),
    url: str = typer.Option("", "--url", help="Published URL."),
    status: str = typer.Option(
        "planned", "--status", "-s", help="Status: planned, writing, review, published."
    ),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Register a new article in the database."""
    heading("Register Article")

    from seedrank.data.articles import register_article
    from seedrank.data.db import connect, get_db_path

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    kw_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else []
    topic_list = [t.strip() for t in topics.split(",") if t.strip()] if topics else []

    with connect(db_path) as conn:
        register_article(
            conn,
            slug=slug,
            title=title,
            target_keywords=kw_list,
            topics=topic_list,
            content_type=content_type,
            url=url or None,
            status=status,
        )

    success(f"Registered article: {slug}")


@articles_app.command(name="update")
def articles_update(
    slug: str = typer.Argument(help="Article slug to update."),
    status: str = typer.Option("", "--status", "-s", help="New status."),
    url: str = typer.Option("", "--url", help="Published URL."),
    published_at: str = typer.Option("", "--published-at", help="Published date (YYYY-MM-DD)."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Update an existing article."""
    heading("Update Article")

    from seedrank.data.articles import update_article
    from seedrank.data.db import connect, get_db_path

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    updates: dict = {}
    if status:
        updates["status"] = status
    if url:
        updates["url"] = url
    if published_at:
        updates["published_at"] = published_at

    if not updates:
        error("No updates provided. Use --status, --url, or --published-at.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        update_article(conn, slug=slug, **updates)

    success(f"Updated article: {slug}")


@articles_app.command(name="crosslinks")
def articles_crosslinks(
    slug: str = typer.Argument(help="Article slug to find crosslinks for."),
    direction: str = typer.Option("both", "--direction", "-d", help="forward, backward, or both."),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    limit: int = typer.Option(10, "--limit", "-n", help="Max suggestions."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Find crosslink suggestions for an article."""
    heading("Crosslink Suggestions")

    from seedrank.articles.crosslinks import find_backward_links, find_forward_links
    from seedrank.data.db import connect, get_db_path

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    results: dict = {}
    with connect(db_path) as conn:
        if direction in ("forward", "both"):
            results["forward"] = find_forward_links(conn, slug, limit=limit)
        if direction in ("backward", "both"):
            results["backward"] = find_backward_links(conn, slug, limit=limit)

    if as_json:
        console.print_json(json.dumps(results, default=str))
        return

    for dir_name, links in results.items():
        info(f"\n{dir_name.title()} links ({len(links)}):")
        if not links:
            info("  No suggestions found.")
            continue
        table_rows = [
            [lnk["slug"], lnk.get("title", "—"), f"{lnk.get('score', 0):.2f}"]
            for lnk in links
        ]
        render_table(f"{dir_name.title()} Links", ["Slug", "Title", "Score"], table_rows)


@articles_app.command(name="schema")
def articles_schema(
    slug: str = typer.Argument(help="Article slug to generate schema for."),
    as_json: bool = typer.Option(True, "--json/--no-json", help="Output as JSON (default)."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Generate JSON-LD structured data for an article."""
    from datetime import date as date_type

    from seedrank.data.db import connect, get_db_path

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    # Load config for Organization and content type info
    config_path = workspace.resolve() / "seedrank.config.yaml"
    org_name = ""
    org_domain = ""
    org_logo = ""
    content_route = "/blog/[slug]"
    if config_path.exists():
        try:
            from seedrank.config.loader import load_config

            cfg = load_config(config_path)
            org_name = cfg.product.name
            org_domain = cfg.product.domain
            for ct in cfg.content_types:
                if ct.slug == "blog":
                    content_route = ct.route
                    break
        except Exception:
            pass

    with connect(db_path) as conn:
        article = conn.execute(
            "SELECT * FROM articles WHERE slug = ?", (slug,)
        ).fetchone()

    if not article:
        error(f"Article '{slug}' not found in database.")
        raise typer.Exit(1)

    article = dict(article)
    today = date_type.today().isoformat()
    published = article.get("published_at") or today
    url = article.get("url") or ""
    if not url and org_domain:
        url_path = content_route.replace("[slug]", slug)
        url = f"https://{org_domain}{url_path}"

    # Build Article/BlogPosting schema
    article_schema: dict = {
        "@type": "BlogPosting",
        "headline": article.get("title", slug),
        "datePublished": published,
        "dateModified": article.get("updated_at") or today,
        "url": url,
    }
    if org_name:
        article_schema["author"] = {
            "@type": "Organization",
            "name": org_name,
        }
        article_schema["publisher"] = {
            "@type": "Organization",
            "name": org_name,
        }
        if org_logo:
            article_schema["publisher"]["logo"] = {
                "@type": "ImageObject",
                "url": org_logo,
            }

    kws = article.get("target_keywords", "[]")
    if isinstance(kws, str):
        import json as json_mod

        kws = json_mod.loads(kws)
    if kws:
        article_schema["keywords"] = kws

    # Build BreadcrumbList
    breadcrumb_schema: dict = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": f"https://{org_domain}/" if org_domain else "/",
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "Blog",
                "item": (
                    f"https://{org_domain}/blog/"
                    if org_domain
                    else "/blog/"
                ),
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": article.get("title", slug),
                "item": url,
            },
        ],
    }

    # Assemble @graph
    graph: dict = {
        "@context": "https://schema.org",
        "@graph": [article_schema, breadcrumb_schema],
    }

    # Add Organization if we have config
    if org_name and org_domain:
        org_schema: dict = {
            "@type": "Organization",
            "name": org_name,
            "url": f"https://{org_domain}/",
        }
        graph["@graph"].append(org_schema)

    console.print_json(json.dumps(graph, indent=2, default=str))


@articles_app.command(name="backlinks")
def articles_backlinks(
    slug: str = typer.Argument(help="Article slug."),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    limit: int = typer.Option(10, "--limit", "-n", help="Max suggestions."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Find articles that should link TO this article (shorthand for --direction backward)."""
    heading("Backward Link Suggestions")

    from seedrank.articles.crosslinks import find_backward_links
    from seedrank.data.db import connect, get_db_path

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        links = find_backward_links(conn, slug, limit=limit)

    if as_json:
        console.print_json(json.dumps(links, default=str))
        return

    if not links:
        info("No backward link suggestions found.")
        return

    table_rows = [
        [lnk["slug"], lnk.get("title", "—"), f"{lnk.get('score', 0):.2f}"]
        for lnk in links
    ]
    render_table("Backward Links", ["Slug", "Title", "Score"], table_rows)
