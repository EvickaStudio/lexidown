"""The optional Requests example preserves server-declared encodings."""

import io
import runpy
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

try:
    import requests
except ImportError:
    requests = None


class LLMExample(unittest.TestCase):
    @unittest.skipIf(requests is None, "Requests is an optional example dependency")
    def test_declared_html_encoding(self):
        for content_type, encoding, text in (
            ("text/html; charset=utf-8", "utf-8", "日本語のページ"),
            ("text/html; charset=windows-1252", "windows-1252", "Crème brûlée €"),
            ("text/html; CHARSET = windows-1252", "windows-1252", "Crème brûlée €"),
        ):
            with self.subTest(content_type=content_type):
                response = requests.Response()
                response.status_code = 200
                response.url = "https://example.com/"
                response.headers["Content-Type"] = content_type
                response.encoding = requests.utils.get_encoding_from_headers(
                    response.headers
                )
                response._content = f"<p>{text}</p>".encode(encoding)
                output = io.StringIO()
                with (
                    patch("requests.get", return_value=response),
                    redirect_stdout(output),
                ):
                    runpy.run_path(
                        Path(__file__).resolve().parents[2] / "examples" / "llm.py"
                    )
                self.assertEqual(output.getvalue(), text + "\n")


if __name__ == "__main__":
    unittest.main()
