"""Tests for the SeleniumWebScraper infrastructure component."""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from pytest_mock import MockerFixture

from cartamercato_grattatore.domain.exceptions.scraping import ScrapingError
from cartamercato_grattatore.infrastructure.scraper_config import (
    RetryConfig,
    ScraperConfig,
)
from cartamercato_grattatore.infrastructure.web_scraper import SeleniumWebScraper


class TestSeleniumWebScraper:
    """Tests for SeleniumWebScraper behavior."""

    @pytest.fixture(autouse=True)
    def _no_real_sleeps(self, mocker: MockerFixture) -> None:
        """Stub time.sleep so human-simulation delays don't slow unit tests."""
        mocker.patch("cartamercato_grattatore.infrastructure.web_scraper.time.sleep")

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
            min_settle_delay=0.0,
            max_settle_delay=0.0,
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

    def test_scrape_when_bot_challenge_present_then_raises_scraping_error(
        self, mock_driver: MagicMock, mock_config: ScraperConfig
    ) -> None:
        """A page stuck on a bot challenge should raise ScrapingError."""
        mock_driver.page_source = (
            "<html><body><h1>Just a moment...</h1>"
            '<iframe src="https://challenges.cloudflare.com/cdn-cgi/challenge-platform/turnstile">'
            "</body></html>"
        )
        mock_driver.find_elements.return_value = []
        config = ScraperConfig(
            headless=True,
            page_load_timeout=5,
            element_wait_timeout=2,
            min_request_delay=0.0,
            max_request_delay=0.0,
            min_settle_delay=0.0,
            max_settle_delay=0.0,
            challenge_timeout=0.0,
            retry=RetryConfig(max_retries=0),
            debug=False,
        )
        scraper = SeleniumWebScraper(config=config)

        with pytest.raises(ScrapingError, match="Bot challenge not resolved"):
            scraper.scrape("https://example.com")

    def test_scrape_when_bot_challenge_resolves_then_returns_content(
        self, mock_driver: MagicMock
    ) -> None:
        """A challenge that auto-resolves should be awaited and scraped normally."""
        challenge_html = "Just a moment... challenge-platform turnstile"
        real_html = "<html><body><div id='tabContent-info'></div></body></html>"
        config = ScraperConfig(
            headless=True,
            page_load_timeout=5,
            element_wait_timeout=2,
            min_request_delay=0.0,
            max_request_delay=0.0,
            min_settle_delay=0.0,
            max_settle_delay=0.0,
            challenge_timeout=5.0,
            retry=RetryConfig(max_retries=0),
            debug=False,
        )
        scraper = SeleniumWebScraper(config=config)

        # page_source sequence: challenge page first, then the real page.
        # A PropertyMock on the mock class acts as a data descriptor, so it
        # takes over reads of the fixture's instance attribute for this scope.
        with patch.object(
            type(mock_driver),
            "page_source",
            new_callable=PropertyMock,
            side_effect=[challenge_html, real_html, real_html, real_html, real_html],
            create=True,
        ):
            # find_elements is polled by EC waits AND the content check; answer
            # [] for the first few polls, then a found element so the challenge
            # is treated as resolved.
            fe_calls = {"n": 0}

            def _find_elements(_self: object, *args: object, **kwargs: object) -> list:
                fe_calls["n"] += 1
                return [] if fe_calls["n"] <= 3 else ["info-container"]

            mock_driver.find_elements.side_effect = _find_elements
            html = scraper.scrape("https://example.com")

        assert html == real_html

    def test_scrape_when_content_marker_missing_then_returns_page_anyway(
        self, mock_driver: MagicMock, mock_config: ScraperConfig
    ) -> None:
        """A page without the content marker (no challenge) returns as-is with a warning."""
        mock_driver.page_source = "<html><body>Unexpected layout</body></html>"
        mock_driver.find_elements.return_value = []
        scraper = SeleniumWebScraper(config=mock_config)

        html = scraper.scrape("https://example.com")

        assert html == mock_driver.page_source
