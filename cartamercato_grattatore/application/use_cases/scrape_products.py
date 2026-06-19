import csv
from pathlib import Path

from loguru import logger

from cartamercato_grattatore.domain.data_models.scraping import ProductURL
from cartamercato_grattatore.domain.exceptions.scraping import ScrapingError
from cartamercato_grattatore.domain.ports.web_scraper import BaseWebScraper


class ScrapeProducts:
    """Use case to scrape product pages and save HTML content.

    Reads a CSV file with product names and URLs, scrapes each page
    using the provided web scraper, and saves the HTML to the
    serialization directory.
    """

    def __init__(self, scraper: BaseWebScraper, serialization_dir: Path) -> None:
        """Initialize the scrape products use case.

        Args:
            scraper: Web scraper implementation to use.
            serialization_dir: Directory to save scraped HTML files.
        """
        self._scraper = scraper
        self._serialization_dir = serialization_dir

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
        """Scrape a product page and save the HTML content.

        Args:
            product: ProductURL containing the product name and URL.
        """
        try:
            html = self._scraper.scrape(str(product.url))
            output_path = self._serialization_dir / f"{product.product_name}.html"
            output_path.write_text(html, encoding="utf-8")
            logger.info("Saved {name} to {path}", name=product.product_name, path=output_path)
        except ScrapingError as e:
            logger.warning("Skipping {name}: {error}", name=product.product_name, error=e)
