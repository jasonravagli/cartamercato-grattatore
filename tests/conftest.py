"""Shared fixtures for the test suite."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from cartamercato_grattatore.infrastructure.scraper_config import RetryConfig, ScraperConfig


@pytest.fixture
def serialization_dir(tmp_path: Path) -> Path:
    """Provide a temporary serialization directory."""
    ser_dir = tmp_path / "serialization"
    ser_dir.mkdir()
    return ser_dir


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Provide a sample CSV file with two products."""
    csv_path = tmp_path / "products.csv"
    csv_path.write_text(
        "product_name,url\nProduct A,https://example.com/a\nProduct B,https://example.com/b\n",
        encoding="utf-8",
    )
    return csv_path


@pytest.fixture
def single_product_csv(tmp_path: Path) -> Path:
    """Provide a CSV file with a single product."""
    csv_path = tmp_path / "products.csv"
    csv_path.write_text(
        "product_name,url\nProduct X,https://example.com/x\n",
        encoding="utf-8",
    )
    return csv_path


@pytest.fixture
def empty_csv(tmp_path: Path) -> Path:
    """Provide a CSV file with only headers."""
    csv_path = tmp_path / "products.csv"
    csv_path.write_text("product_name,url\n", encoding="utf-8")
    return csv_path


@pytest.fixture
def mock_scraper(mocker: MockerFixture) -> MagicMock:
    """Provide a mocked BaseWebScraper instance."""
    mock = mocker.MagicMock()
    mock.scrape.return_value = "<html></html>"
    return mock


@pytest.fixture
def mock_driver(mocker: MockerFixture) -> MagicMock:
    """Provide a mocked Selenium WebDriver instance."""
    driver = mocker.MagicMock()
    driver.page_source = "<html><body>Test</body></html>"
    mocker.patch("selenium.webdriver.Chrome", return_value=driver)
    return driver


@pytest.fixture
def mock_config() -> ScraperConfig:
    """Provide a ScraperConfig with fast defaults for testing."""
    return ScraperConfig(
        headless=True,
        page_load_timeout=5,
        element_wait_timeout=2,
        min_request_delay=0.0,
        max_request_delay=0.0,
        retry=RetryConfig(max_retries=0),
        debug=False,
    )
