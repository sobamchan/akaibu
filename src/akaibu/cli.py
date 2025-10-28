from typing import cast

import click
import sienna
from kensakun import Encoder, Engine
from rich.console import Console
from rich.table import Table

from akaibu import get_library_path, user_dir
from akaibu.checker import Checker
from akaibu.library import Library
from akaibu.paper import PaperAndSummary
from akaibu.summarizer import PaperSummarizer


@click.group()
def cli():
    pass


@cli.command(name="set-endpoint")
@click.argument("url")
@click.argument("key")
def set_endpoint(url: str, key: str):
    path = user_dir() / "endpoint.json"
    sienna.save({"url": url, "key": key}, path)


@cli.command(name="create-feed")
@click.argument("library_name")
@click.argument("url")
@click.argument("requirements")
def create_feed(library_name: str, url: str, requirements: str):
    path = user_dir() / "libraries.json"
    if path.exists():
        libraries: dict[str, str] = sienna.load(path)
    else:
        libraries: dict[str, str] = {}

    to_overwrite = False
    if library_name in libraries.keys():
        to_overwrite_str = input(
            f"{library_name} already exists. Do you want to overwrite it? (y/N)"
        )
        to_overwrite = to_overwrite_str == "y"
        if to_overwrite == "y":
            libraries[library_name] = requirements
        else:
            click.echo("Aborted.")
            return
    else:
        libraries[library_name] = requirements

    library_path = get_library_path(library_name)
    library = Library.load_from_path(library_path, remake=True)
    library.add_url(url)

    sienna.save(libraries, path)


@cli.command(name="digest")
@click.argument("n", default=5)
@click.argument("model_name")
@click.option(
    "library_name",
    "--library",
    "-l",
    default=None,
    help="Name of the target library (run `show-libraries` to check libraries you have). If not specified, all libraryes will be checked.",
)
@click.option(
    "in_markdown",
    "--in-markdown",
    "-m",
    is_flag=True,
    help="if given, the output will be formatetd as markdown, if not, will be a table",
)
@click.option(
    "no_sorting",
    "--no-sorting",
    "-ns",
    is_flag=True,
    help="If given, no semantic embeddings based sorting is applied, it just checks papers chronogically.",
)
def digest_n_documents(
    n: int,
    model_name: str,
    library_name: str | None,
    in_markdown: bool,
    no_sorting: bool,
):
    libraries = cast(dict[str, str], sienna.load(user_dir() / "libraries.json"))

    if library_name:
        if library_name not in libraries.keys():
            click.ClickException(
                f"{library_name} does not exist. Use `create-feed` command to make one."
            )
        library_names = [library_name]
    else:
        library_names = list(libraries.keys())

    # For kensakun
    if not no_sorting:
        encoder = Encoder.from_model_name(
            "Snowflake/snowflake-arctic-embed-m-v1.5",
            truncation_ratio=0.5,
        )
    else:
        encoder = None

    console = Console()
    for library_name in library_names:
        requirement: str = libraries[library_name]
        library_path = get_library_path(library_name)
        library = Library.load_from_path(library_path)

        if len(library.list_urls()) == 0:
            raise click.ClickException(
                "You have not set any arXiv urls. Use `set-feed` do set one."
            )

        library.reader.update_feeds()

        endpoint_path = user_dir() / "endpoint.json"
        if not endpoint_path.exists():
            raise click.ClickException(
                "You have not set endpoint information. Use `set-endpoint` command do set one."
            )

        endpoint: dict[str, str] = sienna.load(endpoint_path)
        base_url = endpoint["url"]
        key = endpoint["key"]

        # get summarizer
        summarizer = PaperSummarizer(requirement, model_name, base_url, key)

        # get checker
        checker = Checker(requirement, model_name, base_url, key)

        # Kensakun
        if not no_sorting:
            kensakun_engine = Engine.init(encoder, top_n=n)
        else:
            kensakun_engine = None

        # process papers
        papers = cast(
            list[PaperAndSummary],
            library.get_papers(n, checker, summarizer, kensakun=kensakun_engine),
        )

        # output
        if in_markdown:
            print("\n".join([p.to_markdown() for p in papers]))
        else:
            table = Table(
                title=library_name,
                show_header=True,
                header_style="bold magenta",
                show_lines=True,
            )
            table.add_column("Title")
            table.add_column("URL")
            table.add_column("Summary")

            for paper in papers:
                table.add_row(paper.paper.title, paper.paper.link, paper.summary)

            console.print(table)


@cli.command(name="remove-library")
@click.argument("name")
def remove_library(name: str):
    path = user_dir() / "libraries.json"
    if path.exists():
        libraries: dict[str, str] = sienna.load(path)
        libraries.pop(name)
        sienna.save(libraries, path)

        path = get_library_path(name)
        if path.exists() and path.is_file():
            path.unlink()
            (path.parent / f"{path.name}.search").unlink()


@cli.command(name="show-libraries")
def show_libraries():
    path = user_dir() / "libraries.json"
    if path.exists():
        libraries: dict[str, str] = sienna.load(path)

        console = Console()
        table = Table(show_header=True, header_style="bold magenta", show_lines=True)
        table.add_column("Name")
        table.add_column("URL")
        table.add_column("Requirement")
        table.add_column("# of Unchecked papers")

        for _name, _requirement in libraries.items():
            library = Library.load_from_path(get_library_path(_name), remake=False)
            url = list(library.reader.get_feeds())[0].url
            table.add_row(
                _name, url, _requirement, str(library.count_unchecked_papers())
            )

        console.print(table)


@cli.command(name="show-past-papers")
@click.argument("library_name")
@click.option(
    "in_markdown",
    "--in-markdown",
    "-m",
    is_flag=True,
)
def show_past_papers(library_name: str, in_markdown: bool):
    libraries = cast(dict[str, str], sienna.load(user_dir() / "libraries.json"))
    if library_name not in libraries.keys():
        click.ClickException(
            f"{library_name} does not exist. Use `create-feed` command to make one."
        )
    library_path = get_library_path(library_name)
    library = Library.load_from_path(library_path)

    papers = library.get_past_relevant_papers()

    if in_markdown:
        print(f"# {library_name}")
        print("\n".join([p.to_markdown() for p in papers]))
    else:
        console = Console()
        table = Table(show_header=True, header_style="bold magenta", show_lines=True)
        table.add_column("Title")
        table.add_column("URL")
        table.add_column("Summary")

        for paper in papers:
            table.add_row(paper.paper.title, paper.paper.link, paper.summary)

        console.print(table)
