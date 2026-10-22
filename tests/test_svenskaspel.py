"""Validate direct feed handling without network requests."""

import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "svenskaspel.py"
spec = importlib.util.spec_from_file_location("svenskaspel", SCRIPT)
svenskaspel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(svenskaspel)


class SvenskaSpelTests(unittest.TestCase):
    def test_raw_response_and_provenance_preserved(self):
        payload = {"events": [{"event": {"id": 123, "state": "STARTED"},
                               "betOffers": [], "liveData": {"test": True}}]}
        with patch.object(svenskaspel, "urlopen",
                          return_value=io.BytesIO(json.dumps(payload).encode())) as fetch:
            result = svenskaspel.fetch()
        self.assertEqual(result["response"], payload)
        self.assertEqual(result["source"], svenskaspel.SOURCE)
        self.assertTrue(result["checked_at"])
        request = fetch.call_args.args[0]
        self.assertEqual(request.full_url, svenskaspel.SOURCE)
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertEqual(fetch.call_args.kwargs["timeout"], 20)

    def test_empty_offering_is_valid(self):
        with patch.object(svenskaspel, "urlopen", return_value=io.BytesIO(b'{"events": []}')):
            self.assertEqual(svenskaspel.fetch()["response"]["events"], [])

    def test_html_and_unexpected_schema_rejected(self):
        for content in (b'<html>Access denied</html>', b'{}', b'[]',
                        b'{"events": [null]}', b'{"events": [{"event": {}}]}'):
            with self.subTest(content=content), \
                    patch.object(svenskaspel, "urlopen", return_value=io.BytesIO(content)):
                with self.assertRaises(svenskaspel.OddsError):
                    svenskaspel.fetch()

    def test_http_failure_is_reported_without_retry_or_browser(self):
        failure = HTTPError(svenskaspel.SOURCE, 403, "Forbidden", {}, None)
        with patch.object(svenskaspel, "urlopen", side_effect=failure) as fetch:
            with self.assertRaisesRegex(svenskaspel.OddsError, 'HTTP 403'):
                svenskaspel.fetch()
            fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
