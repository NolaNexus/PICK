import click

from pick.export import write_export


@click.group()
def cli():
    pass


@cli.command()
@click.option("--mode", default="incremental")
def refresh(mode: str):
    click.echo(f"Refresh mode={mode}")
    write_export()
    click.echo("Export written to public/data/")


@cli.command()
def backfill():
    click.echo("Backfill all tracked pages from wiki")
    write_export()
    click.echo("Export written to public/data/")
