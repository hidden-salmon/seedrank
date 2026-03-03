"""Seedrank CLI — Typer application."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()  # Load .env from cwd (workspace root)

import typer  # noqa: E402

app = typer.Typer(
    name="seedrank",
    help="Seedrank — keyword research, content management, and performance tracking.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def version_callback(value: bool) -> None:
    if value:
        from seedrank import __version__

        typer.echo(f"seedrank {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Seedrank — programmatic SEO toolkit for Claude Code."""


# Register commands
from seedrank.cli.init_cmd import init_cmd  # noqa: E402
from seedrank.cli.status import status_cmd  # noqa: E402

app.command(name="init")(init_cmd)
app.command(name="status")(status_cmd)

# Register sub-app groups
from seedrank.cli.articles import articles_app  # noqa: E402
from seedrank.cli.calendar import calendar_app  # noqa: E402
from seedrank.cli.competitors import competitors_app  # noqa: E402
from seedrank.cli.data import data_app  # noqa: E402
from seedrank.cli.gsc import gsc_app  # noqa: E402
from seedrank.cli.research import research_app  # noqa: E402
from seedrank.cli.session import session_app  # noqa: E402
from seedrank.cli.validate import validate_app  # noqa: E402

app.add_typer(research_app, name="research")
app.add_typer(data_app, name="data")
app.add_typer(articles_app, name="articles")
app.add_typer(calendar_app, name="calendar")
app.add_typer(session_app, name="session")
app.add_typer(gsc_app, name="gsc")
app.add_typer(validate_app, name="validate")
app.add_typer(competitors_app, name="competitors")
