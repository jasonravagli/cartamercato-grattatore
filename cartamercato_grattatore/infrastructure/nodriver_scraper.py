"""Nodriver (stealth Chromium) web scraper for Cloudflare-protected sites.

This is the recommended implementation for Cardmarket. As validated live on
2026-08-16:

- ``selenium`` masked Chrome (headless and visible) is served a Turnstile
  challenge that never auto-resolves.
- ``nodriver`` in headless mode receives a hard block ("Sorry, you have been
  blocked") with no interactive challenge.
- ``nodriver`` in a **visible** window, using a **fresh user-data profile
  per run**, passes the managed challenge (auto-resolved, no manual click
  needed) and loads the real product page in a few seconds. The profile is
  reset at each run start: reusing a profile across runs eventually leads
  Cloudflare to hard-block it (stale ``cf_clearance``), as observed live.

The public interface is synchronous (``scrape``/``close``) to match
:class:`~cartamercato_grattatore.domain.ports.web_scraper.BaseWebScraper`.
Nodriver is asyncio-based, so this scraper owns a single background event
loop in a daemon thread: one browser is created on first use and reused for
every URL of the run, and all calls submit to that loop via
:func:`asyncio.run_coroutine_threadsafe`.
"""

import asyncio
import contextlib
import os
import random
import shutil
import threading
import time
from pathlib import Path
from types import CoroutineType
from typing import override

from loguru import logger
from nodriver.core.browser import Browser
from nodriver.core.tab import Tab

from cartamercato_grattatore.domain.exceptions.scraping import ScrapingError
from cartamercato_grattatore.domain.ports.web_scraper import BaseWebScraper
from cartamercato_grattatore.infrastructure.scraper_config import ScraperConfig

# Case-insensitive markers identifying a Cloudflare interstitial in page text.
_CHALLENGE_MARKERS = ("just a moment", "challenge-platform", "turnstile")
# Distinctive marker of a full hard block (no interactive challenge available).
_HARD_BLOCK_MARKER = "you have been blocked"


class NodriverWebScraper(BaseWebScraper):
    """Web scraper built on nodriver (stealth Chromium) with a per-run profile.

    Uses a visible browser window (config ``headless=False``) because
    headless is hard-blocked by Cardmarket's Cloudflare protection. The
    browser starts from a profile reset at each run: a ``cf_clearance``
    cookie, once obtained, is reused for subsequent pages of the same run.

    A single background event loop drives all nodriver calls. The browser is
    started lazily on the first :meth:`scrape` and closed in :meth:`close`.
    """

    def __init__(self, config: ScraperConfig | None = None) -> None:
        """Initialize the scraper.

        Args:
            config: Scraper configuration. Uses sensible defaults if not
                provided. The profile directory is taken from the
                ``NODRIVER_PROFILE_DIR`` environment variable, or a
                project-local ``data/nodriver-profile`` directory by default.
                The profile is reset (deleted) on every instantiation so each
                run starts from a clean browser state.
        """
        self._config = config or ScraperConfig()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._browser: Browser | None = None
        self._tab: Tab | None = None
        self._profile_dir = self._resolve_profile_dir()
        logger.info(
            "NodriverWebScraper initialized (profile={profile}, headless={headless})",
            profile=self._profile_dir,
            headless=self._config.headless,
        )

    # -- lifecycle ----------------------------------------------------------

    @staticmethod
    def _resolve_profile_dir() -> Path:
        """Return a clean profile directory, wiping any previous one.

        Reusing a profile across runs eventually leads Cloudflare to hard
        block it (stale/flagged ``cf_clearance``), so each scraper instance
        starts from a fresh profile; the cookie, once obtained, is still
        reused for all pages within the same run.
        """
        env_dir = os.environ.get("NODRIVER_PROFILE_DIR")
        path = Path(env_dir) if env_dir else Path("data") / "nodriver-profile"
        # Chrome/nodriver need an absolute user-data-dir; a relative path can
        # resolve against the wrong working directory on some platforms.
        path = path.resolve()
        shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _ensure_browser(self) -> None:
        """Start the background event loop and launch the browser on first use."""
        if self._browser is not None:
            return

        loop = asyncio.new_event_loop()
        loop_thread = threading.Thread(target=loop.run_forever, name="nodriver-loop", daemon=True)
        loop_thread.start()

        self._loop = loop
        self._loop_thread = loop_thread

        async def _launch() -> tuple[Browser, Tab]:
            import nodriver as uc

            uc_config = uc.Config(
                headless=self._config.headless,
                user_data_dir=str(self._profile_dir),
            )
            browser = await uc.start(uc_config)
            # Open one tab that we will reuse for the entire run. Some Windows
            # setups report success here but silently fail to attach to the
            # tab; verify the tab is actually connected before proceeding.
            tab = await browser.get("about:blank")
            await tab.evaluate("1 + 1", return_by_value=True)
            return browser, tab

        future = asyncio.run_coroutine_threadsafe(_launch(), loop)
        self._browser, self._tab = future.result(timeout=self._config.page_load_timeout + 30)
        logger.info("Nodriver browser launched (tab ready)")

    def _submit(self, coro: CoroutineType, timeout: float) -> object:
        """Run a coroutine on the owned loop from this (sync) thread."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    # -- page state helpers -------------------------------------------------

    @staticmethod
    def _extract_value(result: object) -> object:
        """Unwrap nodriver's ``evaluate`` return value.

        Nodriver returns falsy or non-serializable results (e.g. ``0``) as a
        ``RemoteObject`` wrapper; pull the concrete ``value`` out when
        present.
        """
        if result is None:
            return None
        return getattr(result, "value", result)

    async def _eval(self, expression: str) -> object:
        """Evaluate JS on the active tab and return a Python value."""
        assert self._tab is not None
        result = await self._tab.evaluate(expression, return_by_value=True)
        return self._extract_value(result)

    async def _page_state(self) -> tuple[int, list[str]]:
        """Return ``(content_marker_count, challenge_markers_found)``.

        Uses JS evaluation (no DOM node cache) so it is safe to poll
        immediately after navigation, before the document has fully settled
        enough for ``get_content``.
        """
        count = await self._eval(
            f"document.querySelectorAll('{self._config.content_marker}').length"
        )
        try:
            n = int(str(count)) if count is not None else 0
        except ValueError:
            n = 0
        title = (await self._eval("document.title")) or ""
        try:
            body_probe = (
                await self._eval("document.body ? document.body.innerText.slice(0, 512) : ''")
            ) or ""
        except Exception:
            body_probe = ""
        haystack = f"{str(title)} {str(body_probe)}".lower()
        challenges = [m for m in _CHALLENGE_MARKERS if m in haystack]
        return n, challenges

    async def _fetch_content(self) -> str:
        """Get the page HTML, guarding against a transient nodriver quirk.

        Right after navigation ``get_content`` can raise a stale-node
        ``ProtocolException``; retry once after a short pause, then fall back
        to serializing ``<html>`` via JS.
        """
        assert self._tab is not None
        try:
            html = await self._tab.get_content()
            if html:
                return html
        except Exception:
            pass
        await asyncio.sleep(1.0)
        try:
            html = await self._tab.get_content()
            if html:
                return html
        except Exception:
            pass
        html = await self._eval(
            "document.documentElement ? document.documentElement.outerHTML : ''"
        )
        return html if isinstance(html, str) else ""

    # -- public API ---------------------------------------------------------

    @override
    def scrape(self, url: str) -> str:
        """Scrape a web page and return its HTML content.

        Reuses the persistent browser and waits for real content
        (distinguishing a live bot challenge, a hard block, and a rendered
        page) before returning the HTML.

        Args:
            url: The URL of the web page to scrape.

        Returns:
            The HTML content of the web page.

        Raises:
            ScrapingError: If the page cannot be retrieved (hard block, a
                challenge that does not clear, or a timeout).
        """
        logger.info("Scraping {url}", url=url)

        last_exception: Exception | None = None
        total_attempts = self._config.retry.max_retries + 1
        for attempt in range(total_attempts):
            try:
                html = self._scrape_once_blocking(url)
                logger.info("Successfully scraped {url} ({size} bytes)", url=url, size=len(html))
                return html
            except ScrapingError as e:
                last_exception = e
                if attempt < self._config.retry.max_retries:
                    base = self._config.retry.base_delay * self._config.retry.multiplier**attempt
                    delay = max(0.1, base + random.uniform(-0.5, 0.5))
                    logger.warning(
                        "Scraping {url} failed (attempt {a}/{t}), retrying in {d:.1f}s: {err}",
                        url=url,
                        a=attempt + 1,
                        t=total_attempts,
                        d=delay,
                        err=e,
                    )
                    time.sleep(delay)
            except Exception as e:
                raise ScrapingError(f"Failed to scrape {url}") from e
        assert last_exception is not None
        raise last_exception

    def _scrape_once_blocking(self, url: str) -> str:
        """Perform a single scrape attempt, blocking until it completes."""
        self._ensure_browser()
        timeout = self._config.page_load_timeout + self._config.challenge_timeout + 60
        try:
            result = self._submit(self._do_scrape(url), timeout=timeout)
        except TimeoutError as e:
            raise ScrapingError(f"Timed out waiting for {url}") from e
        return str(result)

    async def _do_scrape(self, url: str) -> str:
        """Navigate to *url* on the run's tab and wait for real content."""
        assert self._tab is not None
        assert self._browser is not None

        # Navigate, reusing the run's tab, then let the document settle.
        await self._tab.get(url)
        await asyncio.sleep(2.0)

        deadline = time.monotonic() + self._config.challenge_timeout
        saw_challenge = False
        announced = False

        while True:
            n, challenges = await self._page_state()
            ready = n > 0 and not challenges

            if ready:
                break

            if challenges:
                saw_challenge = True
                if not announced:
                    logger.info(
                        "Bot challenge visible for {url}. If the browser "
                        "window shows a 'Verify you are human' checkbox, "
                        "click it to continue.",
                        url=url,
                    )
                    announced = True

            if time.monotonic() >= deadline:
                title = (await self._eval("document.title")) or ""
                preview = (await self._fetch_content())[:2000].lower()
                if _HARD_BLOCK_MARKER in preview:
                    raise ScrapingError(
                        f"Blocked by site anti-bot protection (hard block) "
                        f"for {url} (title={str(title)!r})"
                    )
                if saw_challenge:
                    raise ScrapingError(
                        f"Bot challenge not resolved for {url} "
                        f"(exceeded {self._config.challenge_timeout:.0f}s; "
                        f"title={str(title)!r})"
                    )
                # No challenge and no marker: proceed and let downstream
                # extraction report the layout mismatch.
                logger.warning(
                    "Content marker '{marker}' not found for {url} "
                    "(no challenge); proceeding anyway.",
                    marker=self._config.content_marker,
                    url=url,
                )
                return await self._fetch_content()

            # Human-like settle while waiting for content.
            await asyncio.sleep(
                random.uniform(self._config.min_settle_delay, self._config.max_settle_delay)
            )

        return await self._fetch_content()

    @override
    def close(self) -> None:
        """Tear down the browser and the background event loop."""
        loop = self._loop
        browser = self._browser
        if loop is not None and browser is not None:
            try:
                # Stop the browser (process + connection) on the loop thread,
                # then cancel lingering tasks so the loop can close cleanly.
                asyncio.run_coroutine_threadsafe(self._shutdown(browser, loop), loop).result(
                    timeout=20
                )
            except Exception as e:
                logger.warning("Error closing nodriver browser: {error}", error=e)
        if loop is not None:
            try:
                loop.call_soon_threadsafe(loop.stop)
            except RuntimeError:
                pass
        if self._loop_thread is not None:
            self._loop_thread.join(timeout=5)
        if loop is not None:
            with contextlib.suppress(Exception):
                loop.close()
        self._loop = None
        self._loop_thread = None
        self._browser = None
        self._tab = None
        logger.info("NodriverWebScraper closed")

    @staticmethod
    async def _shutdown(browser: Browser, loop: asyncio.AbstractEventLoop) -> None:
        """Stop the nodriver browser, draining lingering tasks on the loop."""
        with contextlib.suppress(Exception):
            browser.stop()
        # Cancel lingering tasks nodriver left running (websocket keepalive,
        # connection listener). Exclude the currently-running task so we do not
        # await ourselves, which would deadlock the loop.
        current = asyncio.current_task()
        pending = [t for t in asyncio.all_tasks(loop) if t is not current and not t.done()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.wait(pending, timeout=5)
