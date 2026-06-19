"""Configuration for the Selenium web scraper."""

from pydantic import BaseModel, ConfigDict


class RetryConfig(BaseModel):
    """Configuration for retry behavior with exponential backoff."""

    max_retries: int = 3
    base_delay: float = 2.0
    multiplier: float = 2.0


class ScraperConfig(BaseModel):
    """Configuration for the SeleniumWebScraper.

    All values have sensible defaults for scraping Cardmarket.
    """

    model_config = ConfigDict(frozen=True)

    # Browser settings
    headless: bool = True
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    # Timeouts (seconds)
    page_load_timeout: int = 30
    element_wait_timeout: int = 10

    # Request delay to avoid detection (seconds)
    min_request_delay: float = 1.0
    max_request_delay: float = 3.0

    # Retry configuration
    retry: RetryConfig = RetryConfig()

    # Debug mode: saves HTML and screenshots on failure
    debug: bool = False
