"""Selenium-based web scraper with anti-detection capabilities."""

import random
import time
from typing import override

from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from cartamercato_grattatore.domain.exceptions.scraping import ScrapingError
from cartamercato_grattatore.domain.ports.web_scraper import BaseWebScraper
from cartamercato_grattatore.infrastructure.scraper_config import ScraperConfig


class SeleniumWebScraper(BaseWebScraper):
    """Web scraper implementation using Selenium with headless Chrome.

    Includes anti-detection measures to bypass Cloudflare protection:
    - Chrome options to hide automation indicators
    - JavaScript-based webdriver masking
    - Configurable request delays
    - Content-aware page load waits
    - Retry with exponential backoff
    """

    def __init__(self, config: ScraperConfig | None = None) -> None:
        """Initialize the SeleniumWebScraper.

        Args:
            config: Scraper configuration. Uses sensible defaults if not provided.
        """
        self._config = config or ScraperConfig()
        try:
            self._driver = self._create_driver()
        except Exception as e:
            raise ScrapingError(f"Failed to initialize browser: {e}") from e
        logger.info("SeleniumWebScraper initialized")

    def _create_driver(self) -> webdriver.Chrome:
        """Create a Chrome WebDriver with anti-detection options."""
        options = self._build_options()
        driver = webdriver.Chrome(options=options)

        # Set timeouts
        driver.set_page_load_timeout(self._config.page_load_timeout)
        driver.implicitly_wait(5)

        return driver

    def _build_options(self) -> Options:
        """Build ChromeOptions with anti-detection configuration."""
        options = Options()

        if self._config.headless:
            options.add_argument("--headless=new")

        options.add_argument(f"user-agent={self._config.user_agent}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--window-size=1920,1080")

        # Hide automation indicators
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        return options

    def _mask_webdriver(self) -> None:
        """Execute JavaScript to mask automation indicators in the browser."""
        script = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        """
        self._driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": script})

    def _wait_for_content(self) -> None:
        """Wait for page content to load by checking for body elements."""
        wait = WebDriverWait(self._driver, self._config.element_wait_timeout)
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "div")))
        except TimeoutException:
            logger.warning("Content wait timed out, proceeding anyway")

    def _random_delay(self) -> None:
        """Sleep for a random duration to simulate human behavior."""
        delay = random.uniform(self._config.min_request_delay, self._config.max_request_delay)
        time.sleep(delay)

    @override
    def scrape(self, url: str) -> str:
        """Scrape a web page and return its HTML content.

        Navigates to the URL, waits for content to load, and returns the
        page source. Includes anti-detection measures and random delays.

        Args:
            url: The URL of the web page to scrape.

        Returns:
            The HTML content of the web page.

        Raises:
            ScrapingError: If the scraping operation fails after retries.
        """
        logger.info("Scraping {url}", url=url)

        last_exception: Exception | None = None
        total_attempts = self._config.retry.max_retries + 1

        for attempt in range(total_attempts):
            try:
                html = self._do_scrape(url)
                logger.info("Successfully scraped {url} ({size} bytes)", url=url, size=len(html))
                return html
            except ScrapingError as e:
                last_exception = e
                if attempt < self._config.retry.max_retries:
                    jitter = random.uniform(-0.5, 0.5)
                    base = self._config.retry.base_delay * self._config.retry.multiplier**attempt
                    delay = max(0.1, base + jitter)
                    logger.warning(
                        "Scraping {url} failed (attempt {attempt}/{total}), "
                        "retrying in {delay:.1f}s: {error}",
                        url=url,
                        attempt=attempt + 1,
                        total=total_attempts,
                        delay=delay,
                        error=e,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Scraping {url} failed after {total} attempts: {error}",
                        url=url,
                        total=total_attempts,
                        error=e,
                    )
                    if self._config.debug:
                        self._save_debug(url)

            except Exception as e:
                last_exception = e
                raise ScrapingError(f"Failed to scrape {url}") from e

        # Should not reach here, but satisfy type checker
        raise last_exception  # type: ignore[misc]

    def _do_scrape(self, url: str) -> str:
        """Execute a single scrape attempt for the given URL.

        Args:
            url: The URL of the web page to scrape.

        Returns:
            The HTML content of the web page.

        Raises:
            ScrapingError: If the scraping operation fails.
        """
        try:
            # Mask webdriver before navigation
            self._mask_webdriver()

            # Navigate to the page
            self._driver.get(url)

            # Wait for content to load
            self._wait_for_content()

            # Random delay to avoid detection
            self._random_delay()

            return self._driver.page_source

        except TimeoutException as e:
            raise ScrapingError(f"Page load timeout: {url}") from e
        except WebDriverException as e:
            raise ScrapingError(f"WebDriver error: {url}") from e
        except ScrapingError:
            raise
        except Exception as e:
            raise ScrapingError(f"Failed to scrape {url}") from e

    def _save_debug(self, url: str) -> None:
        """Save HTML and screenshot for debugging when debug mode is enabled.

        Args:
            url: The URL that failed to scrape.
        """
        try:
            import re

            # Sanitize URL to create a safe filename
            safe_url = re.sub(r"[^\w\-]", "_", url)
            safe_url = safe_url[:80]  # Truncate for filesystem safety

            # Save HTML
            html_path = f"/tmp/{safe_url}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self._driver.page_source)
            logger.info("Debug HTML saved to {path}", path=html_path)

            # Save screenshot
            screenshot_path = f"/tmp/{safe_url}.png"
            self._driver.save_screenshot(screenshot_path)
            logger.info("Debug screenshot saved to {path}", path=screenshot_path)

        except Exception as e:
            logger.warning("Failed to save debug files: {error}", error=e)

    @override
    def close(self) -> None:
        """Clean up browser resources."""
        try:
            self._driver.quit()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.warning("Error closing browser: {error}", error=e)
