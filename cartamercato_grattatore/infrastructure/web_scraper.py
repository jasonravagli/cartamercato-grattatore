from typing import override

from cartamercato_grattatore.domain.exceptions.scraping import ScrapingError
from cartamercato_grattatore.domain.ports.web_scraper import BaseWebScraper
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class SeleniumWebScraper(BaseWebScraper):
    """Web scraper implementation using Selenium with headless Chrome."""

    def __init__(self) -> None:
        """Initialize the SeleniumWebScraper with a headless Chrome browser."""
        options = Options()
        options.add_argument("--headless")
        self._driver = webdriver.Chrome(options=options)

    @override
    def scrape(self, url: str) -> str:
        """Scrape a web page and return its HTML content.

        Args:
            url: The URL of the web page to scrape.

        Returns:
            The HTML content of the web page.

        Raises:
            ScrapingError: If the scraping operation fails.
        """
        try:
            self._driver.get(url)
            return self._driver.page_source
        except Exception as e:
            raise ScrapingError(f"Failed to scrape {url}") from e

    @override
    def close(self) -> None:
        """Clean up browser resources."""
        self._driver.quit()
        logger.info("Browser closed successfully")
