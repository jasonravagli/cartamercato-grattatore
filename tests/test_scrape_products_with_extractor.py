"""Tests for ScrapeProducts use case with HTML extraction enabled."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from cartamercato_grattatore.application.use_cases.scrape_products import ScrapeProducts
from cartamercato_grattatore.domain.exceptions.scraping import ExtractionError


class TestScrapeProductsWithExtraction:
    """Tests for the scrape+extract workflow."""

    def test_execute_when_extractor_configured_then_saves_json_alongside_html(
        self,
        single_product_csv: Path,
        mock_scraper: MagicMock,
        serialization_dir: Path,
    ) -> None:
        """With an extractor, both HTML and JSON files should be saved."""
        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = MagicMock(
            model_dump_json=lambda indent=None: '{"product_name": "Product X"}'
        )

        mock_scraper.scrape.return_value = "<html>test</html>"

        use_case = ScrapeProducts(
            scraper=mock_scraper,
            serialization_dir=serialization_dir,
            extractor=mock_extractor,
        )
        use_case.execute(single_product_csv)

        assert (serialization_dir / "Product X.html").exists()
        assert (serialization_dir / "Product X.json").exists()
        mock_extractor.extract.assert_called_once()

    def test_execute_when_extract_raises_extraction_error_then_no_json_saved(
        self,
        single_product_csv: Path,
        mock_scraper: MagicMock,
        serialization_dir: Path,
    ) -> None:
        """If extract raises ExtractionError, HTML is saved but no JSON."""
        mock_extractor = MagicMock()
        mock_extractor.extract.side_effect = ExtractionError("missing structure")

        mock_scraper.scrape.return_value = "<html>no info tab</html>"

        use_case = ScrapeProducts(
            scraper=mock_scraper,
            serialization_dir=serialization_dir,
            extractor=mock_extractor,
        )
        use_case.execute(single_product_csv)

        assert (serialization_dir / "Product X.html").exists()
        assert not (serialization_dir / "Product X.json").exists()

    def test_execute_when_extract_raises_generic_error_then_no_json_saved(
        self,
        single_product_csv: Path,
        mock_scraper: MagicMock,
        serialization_dir: Path,
    ) -> None:
        """If extract raises an unexpected error, HTML is saved but no JSON."""
        mock_extractor = MagicMock()
        mock_extractor.extract.side_effect = TypeError("unexpected")

        mock_scraper.scrape.return_value = "<html>broken</html>"

        use_case = ScrapeProducts(
            scraper=mock_scraper,
            serialization_dir=serialization_dir,
            extractor=mock_extractor,
        )
        use_case.execute(single_product_csv)

        assert (serialization_dir / "Product X.html").exists()
        assert not (serialization_dir / "Product X.json").exists()

    def test_execute_when_no_extractor_then_no_extraction_attempted(
        self,
        single_product_csv: Path,
        mock_scraper: MagicMock,
        serialization_dir: Path,
    ) -> None:
        """Without an extractor, behavior is unchanged from original."""
        mock_scraper.scrape.return_value = "<html>test</html>"

        use_case = ScrapeProducts(
            scraper=mock_scraper,
            serialization_dir=serialization_dir,
        )
        use_case.execute(single_product_csv)

        assert (serialization_dir / "Product X.html").exists()
        assert not (serialization_dir / "Product X.json").exists()

    def test_execute_when_extractor_provided_then_json_contains_valid_data(
        self,
        single_product_csv: Path,
        mock_scraper: MagicMock,
        serialization_dir: Path,
    ) -> None:
        """The saved JSON should contain the extracted data."""
        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = MagicMock(
            model_dump_json=lambda indent=None: json.dumps(
                {"product_name": "Product X", "title": "Test Title", "from_price": "3.00"}
            )
        )

        mock_scraper.scrape.return_value = "<html>test</html>"

        use_case = ScrapeProducts(
            scraper=mock_scraper,
            serialization_dir=serialization_dir,
            extractor=mock_extractor,
        )
        use_case.execute(single_product_csv)

        data = json.loads((serialization_dir / "Product X.json").read_text())
        assert data["product_name"] == "Product X"
        assert data["title"] == "Test Title"
        assert data["from_price"] == "3.00"
