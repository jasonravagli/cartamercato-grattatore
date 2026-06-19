"""Tests for the BeautifulSoupCardmarketExtractor infrastructure class."""

from decimal import Decimal

import pytest

from cartamercato_grattatore.domain.exceptions.scraping import ExtractionError
from cartamercato_grattatore.infrastructure.html_extractor import (
    BeautifulSoupCardmarketExtractor,
)

FULL_PAGE_HTML = """
<html>
<body>
<h1>Test Card - 1st Edition</h1>
<div id="tabContent-info">
  <dl class="labeled row mx-auto g-0">
    <dt>Articoli disponibili</dt><dd>224</dd>
    <dt>Da</dt><dd>3,00 €</dd>
    <dt>Tendenza di prezzo</dt><dd><span>4,41 €</span></dd>
    <dt>Prezzo medio 30 giorni</dt><dd><span>5,06 €</span></dd>
    <dt>Prezzo medio 7 giorni</dt><dd><span>4,77 €</span></dd>
    <dt>Prezzo medio 1 giorno</dt><dd><span>3,73 €</span></dd>
  </dl>
</div>
</body>
</html>
"""

NO_INFO_HTML = "<html><body><h1>Some Page</h1></body></html>"

PARTIAL_INFO_HTML = """
<html>
<body>
<h1>Partial Card</h1>
<div id="tabContent-info">
  <dl class="labeled row mx-auto g-0">
    <dt>Articoli disponibili</dt><dd>1</dd>
    <dt>Da</dt><dd>10,00 €</dd>
  </dl>
</div>
</body>
</html>
"""


class TestBeautifulSoupCardmarketExtractorCanExtract:
    """Tests for the can_extract guard method."""

    def test_can_extract_when_html_has_info_tab_then_returns_true(self) -> None:
        """HTML with tabContent-info should return True."""
        extractor = BeautifulSoupCardmarketExtractor()

        assert extractor.can_extract(FULL_PAGE_HTML) is True

    def test_can_extract_when_html_lacks_info_tab_then_returns_false(self) -> None:
        """HTML without tabContent-info should return False."""
        extractor = BeautifulSoupCardmarketExtractor()

        assert extractor.can_extract(NO_INFO_HTML) is False

    def test_can_extract_when_empty_string_then_returns_false(self) -> None:
        """Empty HTML should return False."""
        extractor = BeautifulSoupCardmarketExtractor()

        assert extractor.can_extract("") is False


class TestBeautifulSoupCardmarketExtractorExtract:
    """Tests for the extract method."""

    def test_extract_when_full_html_then_all_fields_populated(self) -> None:
        """Full HTML should populate all fields correctly."""
        extractor = BeautifulSoupCardmarketExtractor()
        info = extractor.extract(FULL_PAGE_HTML, "Test Card", "https://cardmarket.com/123")

        assert info.product_name == "Test Card"
        assert info.url == "https://cardmarket.com/123"
        assert info.title == "Test Card - 1st Edition"
        assert info.available_items == 224
        assert info.from_price == Decimal("3.00")
        assert info.price_trend == Decimal("4.41")
        assert info.avg_price_30_days == Decimal("5.06")
        assert info.avg_price_7_days == Decimal("4.77")
        assert info.avg_price_1_day == Decimal("3.73")

    def test_extract_when_partial_html_then_known_fields_only(self) -> None:
        """Partial HTML should populate only available fields."""
        extractor = BeautifulSoupCardmarketExtractor()
        info = extractor.extract(PARTIAL_INFO_HTML, "Partial", "https://example.com")

        assert info.available_items == 1
        assert info.from_price == Decimal("10.00")
        assert info.price_trend is None
        assert info.avg_price_7_days is None

    def test_extract_when_no_info_tab_then_raises_extraction_error(self) -> None:
        """Missing info tab should raise ExtractionError."""
        extractor = BeautifulSoupCardmarketExtractor()

        with pytest.raises(ExtractionError, match="tabContent-info"):
            extractor.extract(NO_INFO_HTML, "Test", "https://example.com")

    def test_extract_when_no_h1_tag_then_title_is_none(self) -> None:
        """Missing h1 should result in title=None, not an error."""
        html = """
        <html><body>
        <div id="tabContent-info">
          <dl><dt>Da</dt><dd>1,00 €</dd></dl>
        </div></body></html>
        """
        extractor = BeautifulSoupCardmarketExtractor()
        info = extractor.extract(html, "NoTitle", "https://example.com")

        assert info.title is None
        assert info.from_price == Decimal("1.00")

    def test_extract_when_span_wrapped_values_then_parses_correctly(self) -> None:
        """Values wrapped in <span> tags should parse correctly."""
        extractor = BeautifulSoupCardmarketExtractor()
        info = extractor.extract(FULL_PAGE_HTML, "Test", "https://example.com")

        assert info.price_trend == Decimal("4.41")
        assert info.avg_price_30_days == Decimal("5.06")

    def test_extract_when_unrecognized_label_then_skips_silently(self) -> None:
        """Unknown dt labels should be skipped without errors."""
        html = """
        <html><body>
        <h1>Test</h1>
        <div id="tabContent-info">
          <dl>
            <dt>Unknown Label</dt><dd>value</dd>
            <dt>Da</dt><dd>2,50 €</dd>
          </dl>
        </div></body></html>
        """
        extractor = BeautifulSoupCardmarketExtractor()
        info = extractor.extract(html, "Test", "https://example.com")

        assert info.from_price == Decimal("2.50")

    def test_extract_when_malformed_price_then_field_is_none(self) -> None:
        """Malformed price text should result in None for that field."""
        html = """
        <html><body>
        <h1>Test</h1>
        <div id="tabContent-info">
          <dl>
            <dt>Da</dt><dd>not-a-price</dd>
          </dl>
        </div></body></html>
        """
        extractor = BeautifulSoupCardmarketExtractor()
        info = extractor.extract(html, "Test", "https://example.com")

        assert info.from_price is None

    def test_extract_when_euro_symbol_variant_then_parses(self) -> None:
        """Euro sign character variants should all parse correctly."""
        html = """
        <html><body>
        <h1>Test</h1>
        <div id="tabContent-info">
          <dl>
            <dt>Da</dt><dd>1,50€</dd>
          </dl>
        </div></body></html>
        """
        extractor = BeautifulSoupCardmarketExtractor()
        info = extractor.extract(html, "Test", "https://example.com")

        assert info.from_price == Decimal("1.50")

    def test_extract_when_price_without_currency_symbol_then_parses(self) -> None:
        """Price without currency symbol should still parse."""
        html = """
        <html><body>
        <h1>Test</h1>
        <div id="tabContent-info">
          <dl>
            <dt>Da</dt><dd>2,50</dd>
          </dl>
        </div></body></html>
        """
        extractor = BeautifulSoupCardmarketExtractor()
        info = extractor.extract(html, "Test", "https://example.com")

        assert info.from_price == Decimal("2.50")

    def test_extract_when_whitespace_in_labels_then_parsed(self) -> None:
        """Labels with extra whitespace should still be matched."""
        html = """
        <html><body>
        <h1>Test</h1>
        <div id="tabContent-info">
          <dl>
            <dt>  Da  </dt><dd>  3,50 €  </dd>
          </dl>
        </div></body></html>
        """
        extractor = BeautifulSoupCardmarketExtractor()
        info = extractor.extract(html, "Test", "https://example.com")

        assert info.from_price == Decimal("3.50")

    def test_extract_when_malformed_items_then_field_is_none(self) -> None:
        """Non-numeric items value should result in None."""
        html = """
        <html><body>
        <div id="tabContent-info">
          <dl>
            <dt>Articoli disponibili</dt><dd>--</dd>
          </dl>
        </div></body></html>
        """
        extractor = BeautifulSoupCardmarketExtractor()
        info = extractor.extract(html, "Test", "https://example.com")

        assert info.available_items is None

    def test_extract_when_price_has_thousands_separator_then_parses(self) -> None:
        """European price with thousands separator should parse correctly."""
        html = """
        <html><body>
        <h1>Test</h1>
        <div id="tabContent-info">
          <dl>
            <dt>Da</dt><dd>1.234,50 €</dd>
          </dl>
        </div></body></html>
        """
        extractor = BeautifulSoupCardmarketExtractor()
        info = extractor.extract(html, "Test", "https://example.com")

        assert info.from_price == Decimal("1234.50")

    def test_extract_when_items_has_thousands_separator_then_parsed(self) -> None:
        """Available items with a thousands separator should be parsed correctly."""
        html = """
        <html><body>
        <div id="tabContent-info">
          <dl>
            <dt>Articoli disponibili</dt><dd>1.234</dd>
          </dl>
        </div></body></html>
        """
        extractor = BeautifulSoupCardmarketExtractor()
        info = extractor.extract(html, "Test", "https://example.com")

        assert info.available_items == 1234
