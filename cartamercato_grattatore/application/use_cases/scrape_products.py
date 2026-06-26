"""Use case to scrape product pages and save HTML content."""

import csv
import random
import time
from pathlib import Path

from loguru import logger

from cartamercato_grattatore.domain.data_models.scraping import ProductURL
from cartamercato_grattatore.domain.exceptions.scraping import (
    ExtractionError,
    ScrapingError,
)
from cartamercato_grattatore.domain.ports.html_extractor import BaseHtmlExtractor
from cartamercato_grattatore.domain.ports.web_scraper import BaseWebScraper


class ScrapeProducts:
    """Use case to scrape product pages and save HTML content.

    Reads a CSV file with product names and URLs, scrapes each page
    using the provided web scraper, and saves the HTML to the
    serialization directory. Optionally extracts structured product
    data and saves it as JSON.
    """

    def __init__(
        self,
        scraper: BaseWebScraper,
        serialization_dir: Path,
        extractor: BaseHtmlExtractor | None = None,
    ) -> None:
        """Initialize the scrape products use case.

        Args:
            scraper: Web scraper implementation to use.
            serialization_dir: Directory to save scraped HTML files.
            extractor: Optional HTML extractor for structured data.
        """
        self._scraper = scraper
        self._serialization_dir = serialization_dir
        self._extractor = extractor

        self._min_req_delay = 30.0
        self._max_req_delay = 45.0

    def execute(self, csv_path: Path) -> None:
        """Execute the scraping process for products listed in the CSV file.

        Reads the CSV file, scrapes each product page sequentially,
        and saves the HTML content. Failed URLs are logged and skipped.

        Args:
            csv_path: Path to the CSV file with product_name,url columns.
        """
        products = self._load_products(csv_path)
        logger.info("Loaded {count} products to scrape", count=len(products))

        for product in products:
            self._scrape_and_save(product)

            s_delay = random.uniform(self._min_req_delay, self._max_req_delay)
            logger.info("Waiting {delay:.1f}s before next request", delay=s_delay)
            time.sleep(s_delay)

        self._scraper.close()
        logger.info("Scraping completed")

    def _load_products(self, csv_path: Path) -> list[ProductURL]:
        """Load product URLs from a CSV file.

        Args:
            csv_path: Path to the CSV file.

        Returns:
            List of ProductURL objects.
        """
        products = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                products.append(ProductURL(product_name=row["product_name"], url=row["url"]))
        return products

    def _scrape_and_save(self, product: ProductURL) -> None:
        """Scrape a product page, save HTML, and optionally extract info.

        Args:
            product: ProductURL containing the product name and URL.
        """
        try:
            html = self._scraper.scrape(str(product.url))
            output_path = self._serialization_dir / f"{product.product_name}.html"
            output_path.write_text(html, encoding="utf-8")
            logger.info("Saved {name} to {path}", name=product.product_name, path=output_path)

            if self._extractor is not None:
                self._extract_and_save(product, html)

        except ScrapingError as e:
            logger.warning("Skipping {name}: {error}", name=product.product_name, error=e)

    def _extract_and_save(self, product: ProductURL, html: str) -> None:
        """Extract structured data from HTML and save as JSON.

        Args:
            product: ProductURL containing the product name and URL.
            html: The raw HTML content to extract from.
        """
        try:
            info = self._extractor.extract(html, product.product_name, str(product.url))
            json_path = self._serialization_dir / f"{product.product_name}.json"
            json_path.write_text(info.model_dump_json(indent=2), encoding="utf-8")
            logger.info(
                "Saved JSON for {name} to {path}",
                name=product.product_name,
                path=json_path,
            )
        except ExtractionError as e:
            logger.warning(
                "Extraction failed for {name}: {error}",
                name=product.product_name,
                error=e,
            )
        except Exception as e:
            logger.warning(
                "Unexpected error during extraction for {name}: {error}",
                name=product.product_name,
                error=e,
            )
