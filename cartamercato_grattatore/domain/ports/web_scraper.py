from abc import ABC, abstractmethod


class BaseWebScraper(ABC):
    """Abstract interface defining web scraper functionality."""

    @abstractmethod
    def scrape(self, url: str) -> str:
        """Scrape a web page and return its HTML content.

        Args:
            url: The URL of the web page to scrape.

        Returns:
            The HTML content of the web page.

        Raises:
            ScrapingError: If the scraping operation fails.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Clean up browser resources."""
        pass
