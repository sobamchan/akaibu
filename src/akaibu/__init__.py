from pathlib import Path
from typing import cast

import click
import sienna


def user_dir() -> Path:
    path = Path(click.get_app_dir("io.sotaro.akaibu"))
    path.mkdir(exist_ok=True, parents=True)
    return path


def get_endpoint() -> dict[str, str]:
    path = user_dir() / "endpoint.json"
    endpoint = cast(dict[str, str], sienna.load(path))
    return endpoint


def get_library_path(name: str | None) -> Path:
    name = "default" if not name else name
    path = user_dir() / f"{name}.sqlite"
    return path
