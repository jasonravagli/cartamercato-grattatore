"""Selenium-based web scraper with anti-detection capabilities."""

import random
import time
from typing import cast, override

from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from cartamercato_grattatore.domain.exceptions.scraping import ScrapingError
from cartamercato_grattatore.domain.ports.web_scraper import BaseWebScraper
from cartamercato_grattatore.infrastructure.scraper_config import ScraperConfig

_CHALLENGE_MARKERS = ("just a moment", "challenge-platform", "turnstile")


class SeleniumWebScraper(BaseWebScraper):
    """Web scraper implementation using Selenium with headless Chrome.

    Includes anti-detection measures to bypass Cloudflare protection:
    - Chrome options to hide automation indicators
    - JavaScript-based webdriver masking
    - Configurable request delays
    - Content-aware page load waits
    - Bot challenge (Cloudflare) detection with hard failure
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
        """Wait for initial page content to load by checking for body elements."""
        wait = WebDriverWait(self._driver, self._config.element_wait_timeout)
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "div")))
        except TimeoutException:
            logger.warning("Content wait timed out, proceeding anyway")

    def _simulate_human_activity(self) -> None:
        """Simulate human page interaction: move the mouse, pause, then scroll.

        Anti-bot systems (e.g. Cloudflare) watch for post-load interaction
        signals. Moving the pointer, pausing like a human reading the page,
        and scrolling encourages lazy-loaded content to materialize and adds
        behavioral signals that a non-bot visitor would produce.
        """
        try:
            body = self._driver.find_element(By.TAG_NAME, "body")

            # Move the pointer along a few irregular points.
            locations = [
                (0.3, 0.2),
                (0.6, 0.4),
                (0.45, 0.65),
                (0.7, 0.8),
            ]
            for x_ratio, y_ratio in locations:
                self._move_to(body, x_ratio, y_ratio)
                time.sleep(random.uniform(0.15, 0.6))

            # Human-like reading pause between moving and scrolling.
            time.sleep(random.uniform(0.8, 2.0))

            # Scroll down in a couple of steps to trigger lazy loading.
            for step in (250, 400):
                self._driver.execute_script(f"window.scrollBy(0, {step});")
                time.sleep(random.uniform(0.3, 0.8))
        except WebDriverException as e:
            logger.warning("Human activity simulation skipped: {error}", error=e)

    def _move_to(self, element: WebElement, x_ratio: float, y_ratio: float) -> None:
        """Move the pointer to a fractional position (0-1) of the element."""
        size: dict[str, int] = cast("dict[str, int]", element.size)
        x = max(0, int(size["width"] * x_ratio))
        y = max(0, int(size["height"] * y_ratio))
        ActionChains(self._driver).move_by_offset(x, y).perform()

    def _wait_for_settle(self) -> None:
        """Wait a randomized interval for dynamic content and anti-bot checks to settle."""
        delay = random.uniform(self._config.min_settle_delay, self._config.max_settle_delay)
        logger.debug("Waiting {delay:.1f}s for the page to settle", delay=delay)
        time.sleep(delay)

    def _check_page_state(self) -> tuple[bool, bool]:
        """Check page source for bot challenges and real content.

        Returns:
            A tuple (challenge_present, content_present) where
            challenge_present is True if any known bot challenge marker is
            found in the page source, and content_present is True if the
            configured content_marker element exists in the DOM.
        """
        page_source = self._driver.page_source.lower()
        challenge_present = any(marker in page_source for marker in _CHALLENGE_MARKERS)
        content_present = self._driver.find_elements(By.CSS_SELECTOR, self._config.content_marker)
        return challenge_present, bool(content_present)

    def _wait_for_real_content(self, url: str) -> None:
        """Wait until the page shows real content, retrying if a bot challenge is active.

        Polls the page source until the configured content_marker is present.
        If a bot challenge (e.g. Cloudflare Turnstile) is detected, waits up to
        challenge_timeout seconds for it to auto-resolve before giving up.

        Raises:
            ScrapingError: If a bot challenge is still active after challenge_timeout.
        """
        deadline = time.monotonic() + self._config.challenge_timeout
        poll_interval = 2.0

        while True:
            challenge, content = self._check_page_state()

            if content and not challenge:
                return
            if challenge:
                if time.monotonic() >= deadline:
                    msg = (
                        f"Bot challenge not resolved for {url} "
                        f"(exceeded {self._config.challenge_timeout:.0f}s)"
                    )
                    raise ScrapingError(msg)
                logger.debug("Bot challenge detected for {url}, waiting for auto-resolve", url=url)
                time.sleep(poll_interval)
                continue
            # No challenge and no content — page loaded but marker missing (layout change?)
            logger.warning(
                "Content marker '{marker}' not found for {url}; "
                "page may have changed layout. Proceeding anyway.",
                marker=self._config.content_marker,
                url=url,
            )
            return

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

            # Wait for initial content to load
            self._wait_for_content()

            # Simulate human interaction while the page finishes loading
            self._simulate_human_activity()

            # Wait for real content (detection of bot challenges)
            self._wait_for_real_content(url)

            # Final wait so dynamic content and anti-bot checks settle
            self._wait_for_settle()

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
