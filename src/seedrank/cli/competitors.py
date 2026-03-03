"""seedrank competitors — Manage competitor profiles."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import typer

from seedrank.utils.console import console, error, heading, info, render_table, success, warning

competitors_app = typer.Typer(
    help="Competitor profile management.", no_args_is_help=True
)


@competitors_app.command(name="init")
def competitors_init(
    slug: str = typer.Argument(help="Competitor slug (e.g. 'vercel')."),
    name: str = typer.Option("", "--name", "-n", help="Competitor display name."),
    domain: str = typer.Option("", "--domain", "-d", help="Competitor domain."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Create a skeleton JSON profile for a competitor in data/competitors/."""
    heading("Init Competitor Profile")

    display_name = name or slug.title()
    comp_domain = domain or f"{slug}.com"

    from seedrank.data.competitors import get_profile_path, init_profile

    path = get_profile_path(workspace.resolve(), slug)
    if path.exists():
        warning(f"Profile already exists: {path}")
        return

    created = init_profile(workspace.resolve(), slug, display_name, comp_domain)
    success(f"Created competitor profile: {created}")
    info("Edit the JSON file to add product details, pricing, and verification URLs.")


@competitors_app.command(name="show")
def competitors_show(
    slug: str = typer.Argument(help="Competitor slug."),
    as_json: bool = typer.Option(False, "--json", help="Output raw JSON."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Display a competitor profile."""
    from seedrank.data.competitors import check_freshness, load_profile

    try:
        profile = load_profile(workspace.resolve(), slug)
    except FileNotFoundError:
        error(f"No profile for '{slug}'. Run 'seedrank competitors init {slug}' first.")
        raise typer.Exit(1)

    if as_json:
        console.print_json(json.dumps(profile, indent=2))
        return

    heading(f"Competitor: {profile.get('name', slug)}")
    info(f"URL: {profile.get('url', '—')}")
    info(f"Tier: {profile.get('tier', '—')}")

    freshness = check_freshness(workspace.resolve(), slug)
    if freshness["last_verified"]:
        status = "fresh" if freshness["fresh"] else f"stale ({freshness['days_old']} days old)"
        info(f"Last verified: {freshness['last_verified']} ({status})")
    else:
        warning("Last verified: never")

    if profile.get("strengths"):
        info(f"Strengths: {', '.join(profile['strengths'])}")
    if profile.get("limitations"):
        info(f"Limitations: {', '.join(profile['limitations'])}")

    pricing = profile.get("pricing", {})
    if pricing.get("model"):
        info(f"Pricing model: {pricing['model']}")
    if pricing.get("tiers"):
        for tier in pricing["tiers"]:
            if isinstance(tier, dict):
                info(f"  {tier.get('name', '?')}: {tier.get('price', '?')}")
            else:
                info(f"  {tier}")

    console.print()


@competitors_app.command(name="list")
def competitors_list(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """List all competitor profiles with freshness status."""
    from seedrank.data.competitors import list_profiles

    profiles = list_profiles(workspace.resolve())

    if as_json:
        console.print_json(json.dumps(profiles, default=str))
        return

    heading("Competitor Profiles")
    if not profiles:
        info("No competitor profiles found. Run 'seedrank competitors init <slug>' to create one.")
        return

    table_rows = []
    for p in profiles:
        days = p["days_old"]
        if days is not None:
            freshness = f"{days}d ago" if p["fresh"] else f"{days}d ago (STALE)"
        else:
            freshness = "never"
        table_rows.append([
            p["slug"],
            p["name"],
            str(p["tier"]),
            freshness,
        ])

    render_table("Competitors", ["Slug", "Name", "Tier", "Verified"], table_rows)


@competitors_app.command(name="verify")
def competitors_verify(
    slug: str = typer.Argument(help="Competitor slug to verify."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Fetch verification URLs and output content for review.

    Updates last_verified on completion.
    """
    heading(f"Verify Competitor: {slug}")

    from seedrank.data.competitors import load_profile, save_profile

    try:
        profile = load_profile(workspace.resolve(), slug)
    except FileNotFoundError:
        error(f"No profile for '{slug}'. Run 'seedrank competitors init {slug}' first.")
        raise typer.Exit(1)

    verification_urls = profile.get("verification_urls", {})
    if not any(verification_urls.values()):
        warning("No verification URLs configured. Edit the JSON profile to add them.")
        return

    import httpx

    fetched = 0
    for label, url in verification_urls.items():
        if not url:
            info(f"  {label}: (no URL configured)")
            continue

        info(f"  {label}: {url}")
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                # Output first 500 chars for review
                text = resp.text[:500]
                console.print(f"    Status: {resp.status_code} | Size: {len(resp.text)} chars")
                console.print(f"    Preview: {text[:200]}...")
                fetched += 1
        except httpx.HTTPError as e:
            warning(f"    Failed: {e}")

    if fetched > 0:
        profile["last_verified"] = datetime.now(UTC).strftime("%Y-%m-%d")
        save_profile(workspace.resolve(), slug, profile)
        success(f"Updated last_verified to {profile['last_verified']}")
    else:
        warning("No URLs were successfully fetched.")


@competitors_app.command(name="freshness")
def competitors_freshness(
    days: int = typer.Option(30, "--days", "-d", help="Max days before considered stale."),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Check which competitor profiles are stale."""
    from seedrank.data.competitors import list_profiles

    profiles = list_profiles(workspace.resolve())
    results = []
    for p in profiles:
        is_stale = not p["fresh"] or (p["days_old"] is not None and p["days_old"] > days)
        results.append({**p, "stale": is_stale, "threshold_days": days})

    if as_json:
        console.print_json(json.dumps(results, default=str))
        return

    heading(f"Competitor Freshness (threshold: {days} days)")
    stale = [r for r in results if r["stale"]]
    fresh = [r for r in results if not r["stale"]]

    if fresh:
        for r in fresh:
            success(f"  {r['slug']}: verified {r['days_old'] or '?'} days ago")
    if stale:
        for r in stale:
            d = r["days_old"]
            if d is not None:
                warning(f"  {r['slug']}: STALE — {d} days since verification")
            else:
                warning(f"  {r['slug']}: STALE — never verified")

    if not profiles:
        info("No competitor profiles found.")
