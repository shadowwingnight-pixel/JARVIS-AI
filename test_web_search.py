"""Tests for the Brave Search API client without real network access."""

import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from web_search import WebSearchClient, WebSearchError, format_results_for_assistant


class WebSearchClientTests(unittest.TestCase):
    def test_missing_key_is_reported_without_a_request(self):
        with patch("web_search.urlopen") as mock_urlopen:
            with self.assertRaisesRegex(WebSearchError, "not configured"):
                WebSearchClient(api_key="").search("current weather")

        mock_urlopen.assert_not_called()

    @patch("web_search.urlopen")
    def test_search_parses_safe_results(self, mock_urlopen):
        payload = {
            "web": {
                "results": [
                    {
                        "title": "Example result",
                        "url": "https://example.com/article",
                        "description": "A useful current snippet.",
                    },
                    {"title": "Ignored", "url": "file:///unsafe", "description": "No."},
                ]
            }
        }
        response = MagicMock()
        response.read.return_value = json.dumps(payload).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = response

        results = WebSearchClient(api_key="test-key").search("example query")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Example result")
        request = mock_urlopen.call_args.args[0]
        self.assertIn("q=example+query", request.full_url)
        self.assertEqual(request.get_header("X-subscription-token"), "test-key")

    @patch("web_search.urlopen", side_effect=URLError("offline"))
    def test_network_failure_is_graceful(self, _mock_urlopen):
        with self.assertRaisesRegex(WebSearchError, "unavailable"):
            WebSearchClient(api_key="test-key").search("example query")

    def test_empty_results_and_context_are_clear(self):
        context = format_results_for_assistant("example query", [])

        self.assertIn("No current web results", context)


if __name__ == "__main__":
    unittest.main()
