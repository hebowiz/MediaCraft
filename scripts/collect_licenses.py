"""Collect license texts used by the Windows distribution.

Run this script when dependency versions are updated. Generated files are committed so
that release builds do not need network access.
"""

from __future__ import annotations

import shutil
import sys
import urllib.request
from importlib.metadata import distribution
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LICENSE_DIRECTORY = PROJECT_ROOT / "LICENSES"
GNU_LICENSES = {
    "GPL-3.0.txt": "https://www.gnu.org/licenses/gpl-3.0.txt",
    "LGPL-3.0.txt": "https://www.gnu.org/licenses/lgpl-3.0.txt",
}
PACKAGE_LICENSES = {
    "PyAV-BSD-3-Clause.txt": ("av", "licenses/LICENSE.txt"),
    "python-mpv-GPL.txt": ("mpv", "licenses/LICENSE.GPL"),
    "python-mpv-LGPL.txt": ("mpv", "licenses/LICENSE.LGPL"),
    "PyInstaller.txt": ("pyinstaller", "licenses/COPYING.txt"),
}


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "MediaCraft-license-tool"})
    with urllib.request.urlopen(request, timeout=30) as response:
        destination.write_bytes(response.read())


def _copy_distribution_file(package: str, relative_name: str, destination: Path) -> None:
    package_distribution = distribution(package)
    source = next(
        (
            Path(package_distribution.locate_file(item))
            for item in package_distribution.files or ()
            if item.as_posix().endswith(relative_name)
        ),
        None,
    )
    if source is None or not source.is_file():
        raise FileNotFoundError(f"License file not found for {package}: {relative_name}")
    shutil.copyfile(source, destination)


def main() -> int:
    LICENSE_DIRECTORY.mkdir(exist_ok=True)
    for filename, url in GNU_LICENSES.items():
        _download(url, LICENSE_DIRECTORY / filename)

    shutil.copyfile(
        Path(sys.base_prefix) / "LICENSE.txt",
        LICENSE_DIRECTORY / "Python-3.11.txt",
    )
    for filename, (package, relative_name) in PACKAGE_LICENSES.items():
        _copy_distribution_file(
            package,
            relative_name,
            LICENSE_DIRECTORY / filename,
        )

    shutil.copyfile(LICENSE_DIRECTORY / "GPL-3.0.txt", PROJECT_ROOT / "LICENSE")
    print(f"Collected licenses in {LICENSE_DIRECTORY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
