# tests/test_sale_lookup.py
import pytest
from unittest.mock import patch, MagicMock
from sale_lookup import search_sale_time


def test_search_finds_time():
    mock_result = {
        "organic_results": [
            {"snippet": "Tickets go on sale at 10:00 AM EST on April 15, 2026"}
        ]
    }
    with patch("sale_lookup.GoogleSearch") as MockSearch:
        instance = MockSearch.return_value
        instance.get_dict.return_value = mock_result
        result = search_sale_time("Concert Presale", "serpkey123")
    assert result is not None
    assert "10" in result


def test_search_no_results():
    mock_result = {"organic_results": []}
    with patch("sale_lookup.GoogleSearch") as MockSearch:
        instance = MockSearch.return_value
        instance.get_dict.return_value = mock_result
        result = search_sale_time("Obscure Event", "serpkey123")
    assert result is None


def test_search_api_failure():
    with patch("sale_lookup.GoogleSearch") as MockSearch:
        instance = MockSearch.return_value
        instance.get_dict.side_effect = Exception("API error")
        result = search_sale_time("Concert", "serpkey123")
    assert result is None
