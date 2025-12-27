"""Command-line interface for causaliq-analysis."""

import click

from . import __version__


@click.command(name="causaliq-analysis")
@click.version_option(version=__version__)
@click.argument(
    "name",
    metavar="NAME",
    required=True,
    nargs=1,
)
@click.option("--greet", default="Hello", help="Greeting to use")
def cli(name: str, greet: str) -> None:
    """
    Simple CLI example.

    NAME is the person to greet
    """
    click.echo(f"{greet}, {name}!")


def main() -> None:
    """Entry point for the CLI."""
    cli(prog_name="causaliq-analysis (cqalys)")


if __name__ == "__main__":  # pragma: no cover
    main()
