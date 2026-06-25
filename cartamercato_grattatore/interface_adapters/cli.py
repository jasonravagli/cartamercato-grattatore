"""CLI entry point with dependency injection wiring."""

import argparse
import signal
import sys
import time
from pathlib import Path

import schedule
from loguru import logger

from cartamercato_grattatore.application.use_cases.publish_to_sheets import PublishToSheets
from cartamercato_grattatore.application.use_cases.scrape_products import ScrapeProducts
from cartamercato_grattatore.global_utils.global_context import GlobalContextManager
from cartamercato_grattatore.infrastructure.google_sheets import GspreadSheetsWriter
from cartamercato_grattatore.infrastructure.html_extractor import (
    BeautifulSoupCardmarketExtractor,
)
from cartamercato_grattatore.infrastructure.scraper_config import ScraperConfig
from cartamercato_grattatore.infrastructure.web_scraper import SeleniumWebScraper

DEFAULT_CSV_PATH = Path("assets/products.csv")
DEFAULT_SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1MTOKCjuNwgSbbgLw_bGHk8ZB3oIb2oBmSeyGtRkgD2E/edit?gid=1368179043#gid=1368179043/"


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
    parser.add_argument(
        "--google-spreadsheet-url",
        type=str,
        default=DEFAULT_SPREADSHEET_URL,
        help=(f"URL of the target Google Spreadsheet (default: {DEFAULT_SPREADSHEET_URL})"),
    )
    parser.add_argument(
        "--google-credentials-path",
        type=Path,
        default=None,
        help=(
            "Path to the Google Service Account JSON credentials file. "
            "If not provided, the file is read from the "
            "GOOGLE_APPLICATION_CREDENTIALS environment variable."
        ),
    )
    parser.add_argument(
        "--times",
        type=str,
        default=None,
        help=(
            "Comma-separated list of times (HH:MM) at which to run the scraper. "
            "When provided the app stays alive and executes the pipeline at each "
            "scheduled time until interrupted. Example: '09:00,14:00,20:00'"
        ),
    )
    return parser.parse_args(args)


def main() -> None:
    """Initialize and run the CLI application."""
    args = parse_args()

    if args.times is not None:
        run_schedule(args)
    else:
        GlobalContextManager().initialize()
        _execute_pipeline(args)


def _handle_signal(shutdown_flag: list[bool]) -> None:
    """Handle shutdown signals for the scheduler loop."""
    logger.info("Shutdown signal received. Finishing current run...")
    shutdown_flag[0] = True


def run_schedule(args: argparse.Namespace) -> None:
    """Run the scraper at specified times of day until interrupted.

    Each scheduled run creates a fresh serialization directory and
    executes the full scrape + publish pipeline.

    Args:
        args: Parsed CLI arguments containing --times and pipeline config.
    """
    # Setup minimal logger for the scheduler loop (before GlobalContextManager)
    logger.remove()
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time}</green> <level>{message}</level>",
        level="INFO",
    )

    times = [t.strip() for t in args.times.split(",")]
    logger.info("Scheduler started for times: {times}", times=times)
    logger.info("Press Ctrl+C to stop")

    for t in times:
        schedule.every().day.at(t).do(_scheduled_job, args)

    shutdown = [False]

    signal.signal(signal.SIGINT, lambda _s, _f: _handle_signal(shutdown))
    signal.signal(signal.SIGTERM, lambda _s, _f: _handle_signal(shutdown))

    while not shutdown[0]:
        schedule.run_pending()
        time.sleep(10)

    logger.info("Scheduler stopped")


def _scheduled_job(args: argparse.Namespace) -> None:
    """One scheduled invocation: fresh context, scrape, publish.

    Args:
        args: Parsed CLI arguments for the pipeline.
    """
    GlobalContextManager().reset()
    GlobalContextManager().initialize()
    logger.info("=== Scheduled scrape run started ===")
    try:
        _execute_pipeline(args)
        logger.info("=== Scheduled scrape run completed ===")
    except Exception:
        logger.exception("Scheduled run failed")


def _execute_pipeline(args: argparse.Namespace) -> None:
    """Execute the scrape and publish pipeline using the current global context.

    Args:
        args: Parsed CLI arguments for the pipeline.
    """
    logger.info("Executing the scraper pipeline")
    logger.info("Using CSV file: {csv_file}", csv_file=args.csv_file)

    if not args.csv_file.exists():
        logger.error("CSV file not found: {csv_file}", csv_file=args.csv_file)
        raise FileNotFoundError(f"CSV file not found: {args.csv_file}")

    gc = GlobalContextManager()
    ctx = gc.get_global_context()

    scraper = SeleniumWebScraper(config=ScraperConfig())
    try:
        extractor = BeautifulSoupCardmarketExtractor() if args.extract_info else None

        use_case = ScrapeProducts(
            scraper=scraper,
            serialization_dir=ctx.path_serialization_dir,
            extractor=extractor,
        )

        use_case.execute(args.csv_file)

        # Publish to Google Sheets
        credentials_path = args.google_credentials_path
        if credentials_path is not None:
            logger.info("Publishing to Google Sheets: {url}", url=args.google_spreadsheet_url)
            writer = GspreadSheetsWriter(
                spreadsheet_url=args.google_spreadsheet_url,
                credentials_path=credentials_path,
            )
            publish = PublishToSheets(writer=writer)
            publish.execute(ctx.path_serialization_dir)
            logger.info("Google Sheets publishing completed")
    finally:
        scraper.close()
