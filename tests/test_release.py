"""Publication requires complete local artifacts and safe version retries."""

import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from scripts.prepare_release import main, release_files, should_publish


class ReleaseGuard(unittest.TestCase):
    def test_artifact_matrix_and_pypi_version_gate(self):
        platforms = (
            "manylinux2014_x86_64.manylinux_2_28_x86_64",
            "manylinux_2_28_aarch64",
            "musllinux_1_2_x86_64",
            "musllinux_1_2_aarch64",
            "macosx_11_0_x86_64",
            "macosx_11_0_arm64",
            "win_amd64",
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for minor in range(10, 15):
                for platform in platforms:
                    name = f"lexidown-0.1.0-cp3{minor}-cp3{minor}-{platform}.whl"
                    (directory / name).write_bytes(name.encode())
            sdist = directory / "lexidown-0.1.0.tar.gz"
            sdist.write_bytes(b"source archive")
            version, files = release_files(directory)
            self.assertEqual((version, len(files)), ("0.1.0", 36))

            wheel = next(path for path in files.values() if path.suffix == ".whl")
            payload = wheel.read_bytes()
            wheel.unlink()
            with self.assertRaises(ValueError):
                release_files(directory)
            wheel.write_bytes(payload)

            for bad_name in (
                "unexpected.txt",
                "lexidown-0.2.0.tar.gz",
                "lexidown-0.1.0-cp310-cp310-manylinux_2_17_aarch64.whl",
                "lexidown-0.1.0-cp310-abi3-win_amd64.whl",
                "lexidown-0.1.0-cp315-cp315-win_amd64.whl",
                "lexidown-0.1.0-cp310-cp310-macosx_11_0_universal2.whl",
            ):
                with self.subTest(filename=bad_name):
                    extra = directory / bad_name
                    extra.write_bytes(b"unexpected")
                    with self.assertRaises(ValueError):
                        release_files(directory)
                    extra.unlink()
            sdist.unlink()
            with self.assertRaises(ValueError):
                release_files(directory)
            sdist.write_bytes(b"source archive")

            remote = [
                {
                    "filename": name,
                    "digests": {
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
                    },
                }
                for name, path in files.items()
            ]
            cases = (
                ([], True),
                (remote[:1], True),
                (remote, False),
                ([{"filename": entry["filename"]} for entry in remote], False),
                ([{"filename": "unexpected.whl"}], ValueError),
                (remote[:1] * 2, ValueError),
                (
                    [{"filename": remote[0]["filename"], "digests": {"sha256": "bad"}}],
                    ValueError,
                ),
            )
            for published, expected in cases:
                with (
                    self.subTest(published=published),
                    patch(
                        "scripts.prepare_release.urlopen",
                        return_value=io.BytesIO(
                            json.dumps({"urls": published}).encode()
                        ),
                    ) as request,
                ):
                    if expected is ValueError:
                        with self.assertRaises(ValueError):
                            should_publish(version, files)
                    else:
                        self.assertIs(should_publish(version, files), expected)
                    request.assert_called_once_with(
                        "https://pypi.org/pypi/lexidown/0.1.0/json", timeout=30
                    )

            for error in (
                HTTPError("url", 404, "Not Found", {}, None),
                HTTPError("url", 503, "Unavailable", {}, None),
                URLError("offline"),
            ):
                with (
                    self.subTest(error=error),
                    patch("scripts.prepare_release.urlopen", side_effect=error),
                ):
                    if isinstance(error, HTTPError) and error.code == 404:
                        self.assertTrue(should_publish(version, files))
                    else:
                        with self.assertRaises(type(error)):
                            should_publish(version, files)

            output = directory / "github-output"
            for publish in (True, False):
                with (
                    patch("sys.argv", ["prepare_release.py", str(directory)]),
                    patch.dict(os.environ, GITHUB_OUTPUT=str(output)),
                    patch(
                        "scripts.prepare_release.should_publish", return_value=publish
                    ),
                    patch("sys.stdout", new_callable=io.StringIO),
                ):
                    main()
                self.assertEqual(
                    output.read_text(),
                    f"publish={str(publish).lower()}\nversion=0.1.0\n",
                )
                output.unlink()
