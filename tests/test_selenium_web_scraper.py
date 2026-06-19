"""Tests for the SeleniumWebScraper infrastructure component."""

from unittest.mock import MagicMock

import pytest

from cartamercato_grattatore.domain.exceptions.scraping import ScrapingError
from cartamercato_grattatore.infrastructure.scraper_config import (
    RetryConfig,
    ScraperConfig,
)
from cartamercato_grattatore.infrastructure.web_scraper import SeleniumWebScraper


class TestSeleniumWebScraper:
    """Tests for SeleniumWebScraper behavior."""

    # -- Original tests (behavior-focused, unchanged) --

    def test_scrape_when_valid_url_then_returns_page_source(
        self, mock_driver: MagicMock, mock_config: ScraperConfig
    ) -> None:
        """Scraping a valid URL should return the page source."""
        scraper = SeleniumWebScraper(config=mock_config)

        html = scraper.scrape("https://example.com")

        mock_driver.get.assert_called_once_with("https://example.com")
        assert html == mock_driver.page_source

    def test_scrape_when_driver_raises_exception_then_raises_scraping_error(
        self, mock_driver: MagicMock, mock_config: ScraperConfig
    ) -> None:
        """Scraping when the driver fails should raise a ScrapingError."""
        mock_driver.get.side_effect = Exception("Connection refused")
        scraper = SeleniumWebScraper(config=mock_config)

        with pytest.raises(ScrapingError, match="Failed to scrape"):
            scraper.scrape("https://example.com")

    def test_close_when_called_then_quits_driver(
        self, mock_driver: MagicMock, mock_config: ScraperConfig
    ) -> None:
        """Calling close should quit the browser driver."""
        scraper = SeleniumWebScraper(config=mock_config)

        scraper.close()

        mock_driver.quit.assert_called_once()

    # -- New behavior-focused tests --

    def test_scrape_when_url_contains_special_characters_then_handles_correctly(
        self, mock_driver: MagicMock, mock_config: ScraperConfig
    ) -> None:
        """Scraping URLs with query parameters should navigate correctly."""
        scraper = SeleniumWebScraper(config=mock_config)

        scraper.scrape("https://example.com/product?id=123&ref=search")

        mock_driver.get.assert_called_once_with("https://example.com/product?id=123&ref=search")

    def test_scrape_when_driver_unavailable_then_should_raise_scraping_error(
        self, mocker: MagicMock
    ) -> None:
        """Scraping when Chrome driver is not installed should raise a ScrapingError."""
        mocker.patch("selenium.webdriver.Chrome", side_effect=Exception("Chrome not found"))

        with pytest.raises(ScrapingError):
            SeleniumWebScraper()

    def test_scrape_when_retry_exhausted_then_should_raise_scraping_error(
        self, mock_driver: MagicMock
    ) -> None:
        """Scraping after exhausting all retries should raise a ScrapingError."""
        mock_driver.get.side_effect = Exception("Connection refused")
        config = ScraperConfig(
            min_request_delay=0.0,
            max_request_delay=0.0,
            retry=RetryConfig(max_retries=2, base_delay=0.0),
        )

        scraper = SeleniumWebScraper(config=config)

        with pytest.raises(ScrapingError, match="Failed to scrape"):
            scraper.scrape("https://example.com")

    def test_scrape_when_webdriver_exception_occurs_then_should_wrap_in_scraping_error(
        self, mock_driver: MagicMock, mock_config: ScraperConfig
    ) -> None:
        """Scraping when a WebDriverException occurs should wrap it in ScrapingError."""
        from selenium.common.exceptions import WebDriverException

        mock_driver.get.side_effect = WebDriverException("Session not created")
        scraper = SeleniumWebScraper(config=mock_config)

        with pytest.raises(ScrapingError, match="WebDriver error"):
            scraper.scrape("https://example.com")

    def test_close_when_driver_already_closed_then_should_not_raise(
        self, mock_driver: MagicMock, mock_config: ScraperConfig
    ) -> None:
        """Closing an already-closed driver should not raise."""
        mock_driver.quit.side_effect = Exception("invalid session id")
        scraper = SeleniumWebScraper(config=mock_config)

        scraper.close()

    def test_init_when_no_config_provided_then_should_use_defaults(
        self, mock_driver: MagicMock
    ) -> None:
        """Creating a scraper without config should accept and use sensible defaults."""
        scraper = SeleniumWebScraper()

        assert scraper is not None

    def test_init_when_config_provided_then_should_accept_config(
        self, mock_driver: MagicMock, mock_config: ScraperConfig
    ) -> None:
        """Creating a scraper with a custom config should accept it."""
        scraper = SeleniumWebScraper(config=mock_config)

        assert scraper is not None
