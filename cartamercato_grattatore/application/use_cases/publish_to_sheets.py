"""Use case to publish scraped product data to Google Sheets."""

import json
from decimal import Decimal
from pathlib import Path

from loguru import logger

from cartamercato_grattatore.domain.data_models.scraping import CardmarketProductInfo
from cartamercato_grattatore.domain.ports.google_sheets import BaseGoogleSheetsWriter

SHEET_HEADERS = [
    "Data",
    "Articoli disponibili",
    "Prezzo medio 30gg",
    "Prezzo medio 7gg",
    "Prezzo medio 1gg",
]


class PublishToSheets:
    """Use case to write scraped product data to a Google Spreadsheet.

    Reads CardmarketProductInfo JSON files from a serialization directory
    and writes each product's data as a row in its corresponding sheet.
    Sheets are created automatically if they do not exist.
    """

    def __init__(self, writer: BaseGoogleSheetsWriter) -> None:
        """Initialize the publish to sheets use case.

        Args:
            writer: Google Sheets writer implementation to use.
        """
        self._writer = writer

    def execute(self, serialization_dir: Path) -> None:
        """Execute the publish process for all product JSON files.

        Reads all JSON files from the serialization directory, ensures
        each product has a corresponding sheet, and appends data rows.
        Failed products are logged and skipped.

        Args:
            serialization_dir: Directory containing .json product files.
        """
        json_files = sorted(serialization_dir.glob("*.json"))
        logger.info("Found {count} product data files to publish", count=len(json_files))

        for json_file in json_files:
            self._publish_product(json_file)

    def _publish_product(self, json_file: Path) -> None:
        """Load and publish a single product's data to Google Sheets.

        Args:
            json_file: Path to the product JSON file.
        """
        info = self._load_info(json_file)
        if info is None:
            return

        product_name = info.product_name
        logger.info("Publishing data for {name}", name=product_name)

        self._writer.ensure_sheet(product_name, SHEET_HEADERS)
        row = self._build_row(info)
        self._writer.append_row(product_name, row)
        logger.info("Published row for {name}", name=product_name)

    def _load_info(self, json_file: Path) -> CardmarketProductInfo | None:
        """Load CardmarketProductInfo from a JSON file.

        Args:
            json_file: Path to the JSON file.

        Returns:
            Parsed CardmarketProductInfo or None if loading failed.
        """
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            return CardmarketProductInfo(**data)
        except Exception as e:
            logger.warning(
                "Failed to load {file}: {error}",
                file=json_file.name,
                error=e,
            )
            return None

    def _build_row(self, info: CardmarketProductInfo) -> list:
        """Build a row of values from product info.

        Args:
            info: The extracted product information.

        Returns:
            List of values corresponding to SHEET_HEADERS.
        """
        row: list = []
        # Data - formatted as ISO-like datetime string
        row.append(info.extracted_at.strftime("%Y-%m-%d %H:%M:%S"))
        # Articoli disponibili
        row.append(info.available_items if info.available_items is not None else "")
        # Prezzo medio 30gg
        row.append(self._decimal_to_float(info.avg_price_30_days))
        # Prezzo medio 7gg
        row.append(self._decimal_to_float(info.avg_price_7_days))
        # Prezzo medio 1gg
        row.append(self._decimal_to_float(info.avg_price_1_day))
        return row

    @staticmethod
    def _decimal_to_float(value: Decimal | None) -> float | str:
        """Convert a Decimal value to float for Google Sheets, or empty string.

        Args:
            value: The Decimal value to convert.

        Returns:
            Float value or empty string if None.
        """
        if value is None:
            return ""
        return float(value)
