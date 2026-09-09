"""Tests for the NodriverWebScraper infrastructure component.

These tests exercise the real event-loop / thread plumbing of the scraper but
mock out ``nodriver`` so no browser is launched.
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cartamercato_grattatore.domain.exceptions.scraping import ScrapingError
from cartamercato_grattatore.infrastructure.nodriver_scraper import NodriverWebScraper
from cartamercato_grattatore.infrastructure.scraper_config import RetryConfig, ScraperConfig

URL = "https://example.com/product"
CHALLENGED_HTML = "<html><body>Just a moment... turnstile</body></html>"
HARD_BLOCK_HTML = "<html><body>Sorry, you have been blocked.</body></html>"
PRODUCT_HTML = "<html><body><div id='tabContent-info'>hi</div></body></html>"


def _fast_config(**overrides: object) -> ScraperConfig:
    base: dict[str, object] = {
        "min_request_delay": 0.0,
        "max_request_delay": 0.0,
        "min_settle_delay": 0.0,
        "max_settle_delay": 0.0,
        "challenge_timeout": 0.0,
        "retry": RetryConfig(max_retries=0, base_delay=0.0),
        "debug": False,
    }
    base.update(overrides)
    return ScraperConfig(**base)


def _make_eval_side_effect(markers: int, title: str, body: str) -> Callable[..., object]:
    """Return a side effect keyed on the JS expression passed to ``evaluate``.

    ``markers`` is the count returned by the ``querySelectorAll`` call.
    """

    def _side_effect(expression: str, *, return_by_value: bool = False) -> object:
        if "querySelectorAll" in expression:
            return markers
        if "document.title" in expression:
            return title
        if "document.body" in expression:
            return body
        return ""

    return _side_effect


@pytest.fixture
def mock_nodriver(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    """Patch nodriver so no real browser starts; yield (browser, tab) mocks."""
    monkeypatch.setenv("NODRIVER_PROFILE_DIR", str(tmp_path))

    tab: MagicMock = MagicMock()
    tab.evaluate = AsyncMock(return_value=2)
    browser: MagicMock = MagicMock()
    browser.get = AsyncMock(return_value=tab)

    with patch("nodriver.start", new=AsyncMock(return_value=browser)):
        yield browser, tab


class TestNodriverWebScraper:
    """Behavioral tests for NodriverWebScraper."""

    def test_scrape_when_content_marker_present_then_returns_html(
        self, mock_nodriver: tuple[MagicMock, MagicMock]
    ) -> None:
        _, tab = mock_nodriver
        tab.get = AsyncMock(return_value=None)
        tab.evaluate = AsyncMock(
            side_effect=_make_eval_side_effect(1, "Product | Cardmarket", "body")
        )
        tab.get_content = AsyncMock(return_value=PRODUCT_HTML)

        scraper = NodriverWebScraper(config=_fast_config())
        try:
            html = scraper.scrape(URL)
        finally:
            scraper.close()

        assert html == PRODUCT_HTML

    def test_scrape_when_bot_challenge_unresolved_then_raises(
        self, mock_nodriver: tuple[MagicMock, MagicMock]
    ) -> None:
        _, tab = mock_nodriver
        tab.get = AsyncMock(return_value=None)
        tab.evaluate = AsyncMock(
            side_effect=_make_eval_side_effect(0, "Just a moment...", "turnstile")
        )
        tab.get_content = AsyncMock(return_value=CHALLENGED_HTML)

        scraper = NodriverWebScraper(config=_fast_config())
        try:
            with pytest.raises(ScrapingError, match="Bot challenge not resolved"):
                scraper.scrape(URL)
        finally:
            scraper.close()

    def test_scrape_when_hard_block_then_raises(
        self, mock_nodriver: tuple[MagicMock, MagicMock]
    ) -> None:
        _, tab = mock_nodriver
        tab.get = AsyncMock(return_value=None)
        tab.evaluate = AsyncMock(
            side_effect=_make_eval_side_effect(
                0, "Attention Required! | Cloudflare", "you have been blocked"
            )
        )
        tab.get_content = AsyncMock(return_value=HARD_BLOCK_HTML)

        scraper = NodriverWebScraper(config=_fast_config())
        try:
            with pytest.raises(ScrapingError, match="hard block"):
                scraper.scrape(URL)
        finally:
            scraper.close()

    def test_scrape_when_marker_missing_but_no_challenge_then_returns_anyway(
        self, mock_nodriver: tuple[MagicMock, MagicMock]
    ) -> None:
        _, tab = mock_nodriver
        tab.get = AsyncMock(return_value=None)
        tab.evaluate = AsyncMock(
            side_effect=_make_eval_side_effect(0, "Some Page", "unexpected layout")
        )
        tab.get_content = AsyncMock(return_value="<html><body>x</body></html>")

        scraper = NodriverWebScraper(config=_fast_config())
        try:
            html = scraper.scrape(URL)
        finally:
            scraper.close()

        assert html == "<html><body>x</body></html>"

    def test_close_when_called_then_stops_browser_and_loop(
        self, mock_nodriver: tuple[MagicMock, MagicMock]
    ) -> None:
        browser, _ = mock_nodriver
        browser.stop = MagicMock()

        scraper = NodriverWebScraper(config=_fast_config())
        scraper._ensure_browser()
        scraper.close()

        assert browser.stop.called
        assert scraper._loop is None
        assert scraper._browser is None

    def test_close_when_never_launched_then_is_idempotent(
        self, mock_nodriver: tuple[MagicMock, MagicMock]
    ) -> None:
        scraper = NodriverWebScraper(config=_fast_config())
        scraper.close()
        scraper.close()
        assert scraper._loop is None

    # -- unit: value unwrapping -----------------------------------------------

    def test_profile_dir_is_reset_on_init(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A stale profile directory is wiped on every scraper instantiation."""
        profile = tmp_path / "profile"
        (profile / "Default").mkdir(parents=True)
        (profile / "Default" / "Cookies").write_text("stale cf_clearance")
        monkeypatch.setenv("NODRIVER_PROFILE_DIR", str(profile))

        scraper = NodriverWebScraper(config=_fast_config())

        assert scraper._profile_dir == profile
        assert not (profile / "Default" / "Cookies").exists()

    def test_profile_dir_when_env_unset_then_uses_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("NODRIVER_PROFILE_DIR", raising=False)
        monkeypatch.chdir(tmp_path)

        scraper = NodriverWebScraper(config=_fast_config())

        expected = (Path("data") / "nodriver-profile").resolve()
        assert scraper._profile_dir == expected
        assert expected.is_dir()

    def test_extract_value_unwraps_remote_object(self) -> None:
        class _RO:
            value = 7

        assert NodriverWebScraper._extract_value(_RO()) == 7

    def test_extract_value_passes_plain_values_through(self) -> None:
        assert NodriverWebScraper._extract_value("x") == "x"
        assert NodriverWebScraper._extract_value(3) == 3
        assert NodriverWebScraper._extract_value(None) is None
