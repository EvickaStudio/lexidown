"""Validate the complete wheel set and guard versioned PyPI uploads."""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen

PLATFORMS = {
    ("manylinux", "x86_64"),
    ("manylinux", "aarch64"),
    ("musllinux", "x86_64"),
    ("musllinux", "aarch64"),
    ("macosx", "x86_64"),
    ("macosx", "arm64"),
    ("win", "amd64"),
}
EXPECTED = {
    (f"cp3{minor}", *platform) for minor in range(10, 15) for platform in PLATFORMS
}
VERSION = r"[0-9][A-Za-z0-9_.+!]*"


def release_files(directory):
    files = {}
    versions = set()
    targets = set()
    sdists = 0
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Unexpected release entry: {path.name}")
        source = re.fullmatch(rf"lexidown-({VERSION})\.tar\.gz", path.name)
        if source:
            versions.add(source[1])
            sdists += 1
        else:
            wheel = re.fullmatch(
                rf"lexidown-({VERSION})-(cp3\d+)-\2-(.+)\.whl", path.name
            )
            if not wheel:
                raise ValueError(f"Unexpected distribution: {path.name}")
            versions.add(wheel[1])
            wheel_targets = set()
            for tag in wheel[3].split("."):
                platform = re.fullmatch(
                    r"(manylinux|musllinux|macosx)(?:\d+|_\d+_\d+)"
                    r"_(x86_64|aarch64|arm64)|win_(amd64)",
                    tag,
                )
                if not platform:
                    raise ValueError(f"Unexpected wheel platform: {tag}")
                wheel_targets.add(
                    (wheel[2], "win", platform[3])
                    if platform[3]
                    else (wheel[2], platform[1], platform[2])
                )
            if len(wheel_targets) != 1 or not wheel_targets <= EXPECTED:
                raise ValueError(f"Unexpected wheel target: {path.name}")
            if wheel_targets & targets:
                raise ValueError(f"Duplicate wheel target: {path.name}")
            targets.update(wheel_targets)
        files[path.name] = path
    if sdists != 1 or targets != EXPECTED or len(versions) != 1:
        raise ValueError(
            "Release requires exactly 35 wheels and one sdist of one version"
        )
    return versions.pop(), files


def should_publish(version, files):
    url = f"https://pypi.org/pypi/lexidown/{quote(version, safe='')}/json"
    try:
        with urlopen(url, timeout=30) as response:
            published = json.load(response)["urls"]
    except HTTPError as error:
        if error.code == 404:
            return True
        raise
    remote = {entry["filename"]: entry for entry in published}
    if len(remote) != len(published) or not remote.keys() <= files.keys():
        raise ValueError("PyPI contains unexpected release files")
    if remote.keys() == files.keys():
        return False
    for name, entry in remote.items():
        digest = hashlib.sha256(files[name].read_bytes()).hexdigest()
        if entry["digests"]["sha256"] != digest:
            raise ValueError(
                f"Incomplete PyPI release differs at {name}; "
                "rerun the original failed publishing job to use its preserved artifacts"
            )
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    version, files = release_files(args.directory)
    publish = should_publish(version, files)
    output = f"publish={str(publish).lower()}\nversion={version}\n"
    if "GITHUB_OUTPUT" in os.environ:
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
            stream.write(output)
    print(output, end="")


if __name__ == "__main__":
    main()
