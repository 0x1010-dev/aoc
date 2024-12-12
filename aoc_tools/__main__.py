from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import nbformat
from bs4 import BeautifulSoup, NavigableString, Tag
from platformdirs import user_cache_path
from requests import Session
from rich import print
from rich.markdown import Markdown
from typer import Argument, Exit, Typer

# session cookie
cache_path = user_cache_path("aoc-jupyter", ensure_exists=True)
session_cache_file = cache_path / ".session.lock"
rsession = Session()
if session_cache_file.exists():
    with session_cache_file.open("r") as f:
        rsession.cookies.set("session", f.read())

else:
    print(
        "[yellow]Warning:[/] Session key has not been set! You will only be able to request the first part of each puzzle.\n"
    )

app = Typer(
    name="Advent of Code Helper",
    no_args_is_help=True,
)


def md_from_soup(soup: Tag | NavigableString) -> str:
    if isinstance(soup, NavigableString):
        return soup.get_text()

    md = ""
    for child in soup.children:
        match child:
            case Tag(name="h1"):
                md += f"# {md_from_soup(child)}\n"

            case Tag(name="h2"):
                md += f"## {md_from_soup(child)}\n"

            case Tag(name="h3"):
                md += f"### {md_from_soup(child)}\n"

            case Tag(name="h4"):
                md += f"#### {md_from_soup(child)}\n"

            case Tag(name="h5"):
                md += f"##### {md_from_soup(child)}\n"

            case Tag(name="h6"):
                md += f"###### {md_from_soup(child)}\n"

            case Tag(name="em"):
                if "class" in child.attrs and "star" in child["class"]:
                    md += f"***{md_from_soup(child)}***"
                else:
                    md += f"**{md_from_soup(child)}**"

            case Tag(name="p"):
                md += f"{md_from_soup(child)}\n"

            case Tag(name="pre"):
                if code := child.find("code"):
                    md += f"```shell\n{code.get_text()}\n```\n"

            case Tag(name="code"):
                md += f"`{child.get_text()}`"

            case Tag(name="ul"):
                md += f"{md_from_soup(child)}\n"

            case Tag(name="li"):
                md += f"- {md_from_soup(child)}\n"

            case _:
                md += child.get_text()

    return md


@app.command()
def session(key: Annotated[Optional[str], Argument()] = None):
    """Set session key for adventofcode.com."""
    if key:
        key = key.strip()

        if len(key) != 128:
            print(
                f"[warning]Warning:[/] That does not look like a key! Storing anyway."
            )

        with session_cache_file.open("w") as f:
            f.write(key)

        print("Stored session key.")

    elif not session_cache_file.exists():
        print("No session key has been set.")

    else:
        with session_cache_file.open() as f:
            print(f"[blue]Session Key:[/] {f.read()}")


@app.command()
def task(
    day: int,
    part: int,
    output: Annotated[Optional[Path], Argument()] = None,
    year: int = datetime.now().year,
):
    """Fetches requested task. If output file exists, the new task will be appended."""
    try:
        assert 1 <= day <= 15, "There are only 25 days of Advent of Code!"
        assert 2015 <= year <= datetime.now().year, "Advent of Code began on 2015!"
        assert 1 <= part <= 2, "There are only two parts to each task!"

        # fetch description
        response = rsession.get(f"https://adventofcode.com/{year}/day/{day}")
        assert (
            response.status_code != 404
        ), "The task for the day you requested is not yet available."

        soup = BeautifulSoup(response.text, features="html.parser")
        parts = soup.find_all("article", attrs={"class": "day-desc"})
        assert part <= len(parts), "The task part you requested is not available."

        # convert to markdown
        markdown = md_from_soup(parts[part - 1])

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            match output:
                case Path(suffix=".md"):
                    if output.exists():
                        markdown = "\n" + markdown
                    with output.open("a+") as f:
                        f.write(markdown)

                case Path(suffix=".ipynb"):
                    nb = nbformat.v4.new_notebook()

                    if output.exists():
                        with output.open("r") as f:
                            nb = nbformat.read(f, nbformat.NO_CONVERT)

                    nb["cells"].append(nbformat.v4.new_markdown_cell(markdown))

                    with output.open("w") as f:
                        nbformat.write(nb, f)

        else:
            print(Markdown(markdown))

    except AssertionError as e:
        print(e)
        raise Exit(1)


@app.command()
def input(
    day: int,
    output: Annotated[Optional[Path], Argument()] = None,
    year: int = datetime.now().year,
):
    """Fetches the input for the requested task."""
    try:
        assert 1 <= day <= 15, "There are only 25 days of Advent of Code!"
        assert 2015 <= year <= datetime.now().year, "Advent of Code began on 2015!"

        # fetch input
        response = rsession.get(f"https://adventofcode.com/{year}/day/{day}/input")
        assert (
            response.status_code != 404
        ), "The task for the day you requested is not yet available."

        # output
        if output:
            with open(output, "w") as f:
                f.write(response.text)

        else:
            print(response.text)

    except AssertionError as e:
        print(e)
        raise Exit(1)


@app.command()
def submit(day: int, part: int, answer: str, year: int = datetime.now().year):
    """Submits solution for the requested task."""
    try:
        assert 1 <= day <= 15, "There are only 25 days of Advent of Code!"
        assert 2015 <= year <= datetime.now().year, "Advent of Code began on 2015!"
        assert 1 <= part <= 2, "There are only two parts to each task!"

        # fetch input
        response = rsession.post(
            f"https://adventofcode.com/{year}/day/{day}/answer",
            {"level": str(part), "answer": answer},
        )

        soup = BeautifulSoup(response.text, features="html.parser")
        article = soup.find("article")

        if article:
            print(md_from_soup(article))
        else:
            print("[red]Invalid response from AoC![/]")

    except AssertionError as e:
        print(e)
        raise Exit(1)


if __name__ == "__main__":
    app()
