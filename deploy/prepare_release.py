"""Assemble a fresh deployment directory from byttech-site and bot-tech."""

import argparse
import io
from pathlib import Path
import shutil
import subprocess
import tarfile
from tempfile import TemporaryDirectory


SITE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_URL = "https://github.com/RicoElLong/bot-tech.git"
BACKEND_COMMIT = "62bbcbb00bd179b474e70f12fa826c7f308fb80f"
BACKEND_FILES = (
    "bot.py",
    "scheduling.py",
    "storage.py",
    "webapp.py",
    "requirements.txt",
    "assets/welcome.png",
)


def prepare_release(destination: Path) -> None:
    destination = destination.resolve()
    if destination.is_relative_to(SITE_ROOT):
        raise ValueError("Каталог запуска должен быть вне репозитория byttech-site.")
    if destination.exists():
        raise ValueError("Укажите новый каталог запуска. Существующий каталог не изменён.")

    with TemporaryDirectory(prefix=".byttech-", dir=destination.parent) as temporary:
        backend = Path(temporary) / "backend"
        release = Path(temporary) / "release"
        backend.mkdir()
        release.mkdir()
        subprocess.run(["git", "init", "--quiet", str(backend)], check=True)
        subprocess.run(
            ["git", "-C", str(backend), "fetch", "--quiet", "--depth=1",
             BACKEND_URL, BACKEND_COMMIT],
            check=True,
        )
        archive = subprocess.check_output(
            ["git", "-C", str(backend), "archive", BACKEND_COMMIT, *BACKEND_FILES]
        )
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as files:
            files.extractall(release, filter="data")
        shutil.copytree(SITE_ROOT / "web", release / "web")
        release.rename(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="New directory for the release")
    args = parser.parse_args()
    try:
        prepare_release(args.destination)
    except (OSError, ValueError, subprocess.CalledProcessError, tarfile.TarError) as error:
        parser.exit(1, f"{error}\n")
    print(args.destination.resolve())


if __name__ == "__main__":
    main()
