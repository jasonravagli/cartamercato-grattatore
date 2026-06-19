"""Tests for the SeleniumWebScraper infrastructure component."""

from unittest.mock import MagicMock

import pytest
from cartamercato_grattatore.domain.exceptions.scraping import ScrapingError
from cartamercato_grattatore.infrastructure.web_scraper import SeleniumWebScraper


class TestSeleniumWebScraper:
    """Tests for SeleniumWebScraper behavior."""

    def test_scrape_when_valid_url_then_returns_page_source(self, mock_driver: MagicMock) -> None:
        """Scraping a valid URL should return the page source."""
        scraper = SeleniumWebScraper()

        html = scraper.scrape("https://example.com")

        mock_driver.get.assert_called_once_with("https://example.com")
        assert html == mock_driver.page_source

    def test_scrape_when_driver_raises_exception_then_raises_scraping_error(
        self, mock_driver: MagicMock
    ) -> None:
        """Scraping when the driver fails should raise a ScrapingError."""
        mock_driver.get.side_effect = Exception("Connection refused")
        scraper = SeleniumWebScraper()

        with pytest.raises(ScrapingError, match="Failed to scrape"):
            scraper.scrape("https://example.com")

    def test_close_when_called_then_quits_driver(self, mock_driver: MagicMock) -> None:
        """Calling close should quit the browser driver."""
        scraper = SeleniumWebScraper()

        scraper.close()

        mock_driver.quit.assert_called_once()
