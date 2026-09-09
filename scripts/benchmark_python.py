"""Persistent Python benchmark worker; I/O and hashing stay outside timing."""

import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter

from lexidown import TurndownService, _native
from lexidown import __file__ as package_file


def main():
    inputs = {}
    engine = {
        "package_path": str(Path(package_file).resolve().parent),
        "native_binary_path": str(Path(_native.__file__).resolve()),
        "native_binary_sha256": hashlib.sha256(
            Path(_native.__file__).read_bytes()
        ).hexdigest(),
    }
    for line in sys.stdin:
        try:
            request = json.loads(line)
            path = request["path"]
            if path not in inputs:
                inputs[path] = Path(path).read_bytes().decode("utf-8")
            html = inputs[path]
            options = request["options"]
            start = perf_counter()
            output = TurndownService(options).turndown(html)
            elapsed = (perf_counter() - start) * 1000
            encoded = output.encode("utf-8")
            if "output_path" in request:
                Path(request["output_path"]).write_bytes(encoded)
            result = {
                "samples_ms": [elapsed],
                "output_sha256": hashlib.sha256(encoded).hexdigest(),
                "output_bytes": len(encoded),
                **engine,
            }
            # Release the previous result outside the next conversion's timer.
            del output, encoded
        except Exception as error:
            result = {"error": type(error).__name__, "message": str(error)}
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
