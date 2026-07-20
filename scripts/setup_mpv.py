"""Download a project-local Windows libmpv build recommended by mpv.io."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path


RELEASE_TAG = "20260610"
RELEASE_API = (
    "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/tags/"
    f"{RELEASE_TAG}"
)
ASSET_PATTERN = re.compile(r"^mpv-dev-x86_64-\d{8}-git-[^-]+\.7z$")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_DIRECTORY = PROJECT_ROOT / "vendor" / "mpv"


def _request(url: str, *, authenticated: bool = False) -> urllib.request.Request:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "MediaCraft-setup",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if authenticated and token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def main() -> int:
    installed_dll = TARGET_DIRECTORY / "libmpv-2.dll"
    if installed_dll.is_file():
        print(f"libmpv is already installed at {installed_dll}")
        return 0

    with urllib.request.urlopen(
        _request(RELEASE_API, authenticated=True), timeout=30
    ) as response:
        release = json.load(response)

    asset = next(
        (item for item in release["assets"] if ASSET_PATTERN.fullmatch(item["name"])),
        None,
    )
    if asset is None:
        raise RuntimeError("対応するx86_64版libmpvアーカイブが見つかりません。")

    with tempfile.TemporaryDirectory(prefix="mediacraft-mpv-") as temp_name:
        temp_directory = Path(temp_name)
        archive_path = temp_directory / asset["name"]
        print(f"Downloading {asset['name']}...")
        with urllib.request.urlopen(_request(asset["browser_download_url"]), timeout=120) as response:
            archive_path.write_bytes(response.read())

        digest = asset.get("digest")
        if digest and digest.startswith("sha256:"):
            actual = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            if actual != digest.removeprefix("sha256:"):
                raise RuntimeError("libmpvアーカイブのSHA-256検証に失敗しました。")

        extract_directory = temp_directory / "extracted"
        extract_directory.mkdir()
        tar_command = shutil.which("tar")
        if tar_command is None:
            raise RuntimeError("Windows標準のtarコマンドが見つかりません。")
        subprocess.run(
            [tar_command, "-xf", str(archive_path), "-C", str(extract_directory)],
            check=True,
        )

        dll_path = next(extract_directory.rglob("libmpv-2.dll"), None)
        if dll_path is None:
            raise RuntimeError("アーカイブ内にlibmpv-2.dllが見つかりません。")

        TARGET_DIRECTORY.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dll_path, TARGET_DIRECTORY / "libmpv-2.dll")
        (TARGET_DIRECTORY / "BUILD.txt").write_text(
            f"release={release['tag_name']}\nasset={asset['name']}\n",
            encoding="utf-8",
        )

    print(f"Installed libmpv to {TARGET_DIRECTORY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
