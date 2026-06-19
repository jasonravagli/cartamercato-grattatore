"""CLI entry point with dependency injection wiring."""

import argparse
from pathlib import Path

from loguru import logger

from cartamercato_grattatore.application.use_cases.scrape_products import ScrapeProducts
from cartamercato_grattatore.global_utils.global_context import GlobalContextManager
from cartamercato_grattatore.infrastructure.html_extractor import (
    BeautifulSoupCardmarketExtractor,
)
from cartamercato_grattatore.infrastructure.scraper_config import ScraperConfig
from cartamercato_grattatore.infrastructure.web_scraper import SeleniumWebScraper

DEFAULT_CSV_PATH = Path("assets/products.csv")


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Optional list of arguments (useful for testing).

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(description="Scrape product information from Cardmarket.")
    parser.add_argument(
        "--csv-file",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help=f"Path to CSV file with product URLs (default: {DEFAULT_CSV_PATH})",
    )
    parser.add_argument(
        "--extract-info",
        action="store_true",
        default=True,
        help="Also extract structured product data and save as JSON",
    )
    return parser.parse_args(args)


def main() -> None:
    """Initialize and run the CLI application."""
    args = parse_args()

    logger.info("Executing the CLI application")
    logger.info("Using CSV file: {csv_file}", csv_file=args.csv_file)

    if not args.csv_file.exists():
        logger.error("CSV file not found: {csv_file}", csv_file=args.csv_file)
        raise FileNotFoundError(f"CSV file not found: {args.csv_file}")

    gc = GlobalContextManager()
    ctx = gc.get_global_context()

    scraper = SeleniumWebScraper(config=ScraperConfig())

    extractor = BeautifulSoupCardmarketExtractor() if args.extract_info else None

    use_case = ScrapeProducts(
        scraper=scraper,
        serialization_dir=ctx.path_serialization_dir,
        extractor=extractor,
    )

    use_case.execute(args.csv_file)
