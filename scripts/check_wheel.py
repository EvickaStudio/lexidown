"""Check the installed wheel and run the existing suite outside the source tree."""

import importlib.machinery
import importlib.metadata
import unittest
from pathlib import Path

import lexidown
from lexidown import _native


def main():
    distribution = importlib.metadata.distribution("lexidown")
    files = distribution.files or []
    installed = {Path(distribution.locate_file(path)).resolve() for path in files}
    for module in (lexidown, _native):
        assert Path(module.__file__).resolve() in installed, module.__file__
    assert any(
        _native.__file__.endswith(suffix)
        for suffix in importlib.machinery.EXTENSION_SUFFIXES
    ), "The installed conversion engine must be a compiled extension"
    assert lexidown.__version__ == distribution.version

    required = {
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "vendor/lexbor/LICENSE",
        "vendor/lexbor/NOTICE",
        "vendor/lexbor/BSD-LICENSE",
    }
    declared = set(distribution.metadata.get_all("License-File", []))
    assert required <= declared, required - declared
    for name in declared:
        matches = [path for path in files if str(path).endswith(f"/licenses/{name}")]
        assert len(matches) == 1, f"Missing or duplicated packaged license: {name}"
        assert (
            Path(distribution.locate_file(matches[0]))
            .read_text(encoding="utf-8")
            .strip()
        )

    suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
    assert suite.countTestCases(), "No wheel tests were discovered"
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(not result.wasSuccessful())


if __name__ == "__main__":
    main()
