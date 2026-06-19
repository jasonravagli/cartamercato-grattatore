"""HTML extraction implementation for Cardmarket product pages."""

from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup, Tag
from loguru import logger
from overrides import override

from cartamercato_grattatore.domain.data_models.scraping import CardmarketProductInfo
from cartamercato_grattatore.domain.exceptions.scraping import ExtractionError
from cartamercato_grattatore.domain.ports.html_extractor import BaseHtmlExtractor

_LABEL_TO_FIELD: dict[str, str] = {
    "articoli disponibili": "available_items",
    "da": "from_price",
    "tendenza di prezzo": "price_trend",
    "prezzo medio 30 giorni": "avg_price_30_days",
    "prezzo medio 7 giorni": "avg_price_7_days",
    "prezzo medio 1 giorno": "avg_price_1_day",
}


class BeautifulSoupCardmarketExtractor(BaseHtmlExtractor):
    """Extract product information from Cardmarket HTML pages using BeautifulSoup."""

    @override
    def extract(self, html: str, product_name: str, url: str) -> CardmarketProductInfo:
        """Parse HTML and return extracted product information.

        Args:
            html: The raw HTML source of the product page.
            product_name: The product name from the CSV input.
            url: The product URL that was scraped.

        Returns:
            A CardmarketProductInfo model with extracted data.

        Raises:
            ExtractionError: If the expected HTML structure is missing.
        """
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_title(soup)
        info_container = soup.find(id="tabContent-info")

        if info_container is None:
            raise ExtractionError("tabContent-info")

        field_values = self._parse_info_container(info_container)

        return CardmarketProductInfo(
            product_name=product_name,
            url=url,
            title=title,
            **field_values,
        )

    @override
    def can_extract(self, html: str) -> bool:
        """Check whether the HTML contains the expected info structure.

        Args:
            html: The raw HTML source to inspect.

        Returns:
            True if the tabContent-info container is present.
        """
        soup = BeautifulSoup(html, "html.parser")
        return soup.find(id="tabContent-info") is not None

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        """Extract the product title from the <h1> tag.

        Args:
            soup: Parsed BeautifulSoup object.

        Returns:
            The h1 text content, or None if not found.
        """
        h1 = soup.find("h1")
        if h1 is None:
            return None
        return h1.get_text(strip=True) or None

    def _parse_info_container(self, container: Tag) -> dict[str, object]:
        """Parse dt/dd pairs within the info container.

        Args:
            container: The tabContent-info Tag element.

        Returns:
            Dictionary mapping field names to parsed values.
        """
        data: dict[str, object] = {}
        dt_tags = container.find_all("dt")

        for dt in dt_tags:
            label = self._normalize_label(dt.get_text(strip=True))
            field_name = _LABEL_TO_FIELD.get(label)

            if field_name is None:
                continue

            dd = self._find_next_dd(dt)
            if dd is None:
                logger.warning("No <dd> found for label '{label}'", label=label)
                continue

            value = self._parse_value(field_name, dd)
            data[field_name] = value

        return data

    @staticmethod
    def _find_next_dd(dt: Tag) -> Tag | None:
        """Find the <dd> that immediately follows the given <dt>.

        Args:
            dt: The <dt> Tag element.

        Returns:
            The next sibling <dd> Tag, or None.
        """
        sibling = dt.find_next_sibling()
        if sibling and sibling.name == "dd":
            return sibling
        return None

    @staticmethod
    def _parse_value(field_name: str, dd: Tag) -> object:
        """Parse the text content of a <dd> tag into the appropriate type.

        Args:
            field_name: The target field name to determine parsing logic.
            dd: The <dd> Tag element.

        Returns:
            Parsed value (int, Decimal, or None).
        """
        text = dd.get_text(strip=True)
        if not text:
            logger.warning("Empty <dd> for field '{field}'", field=field_name)
            return None

        if field_name == "available_items":
            return _parse_int(text)

        # All mapped fields except available_items are prices
        return _parse_price(text)

    @staticmethod
    def _normalize_label(label: str) -> str:
        """Normalize a label string for matching.

        Removes zero-width characters, normalizes whitespace,
        converts to lowercase.

        Args:
            label: The raw label text.

        Returns:
            Normalized label string.
        """
        normalized = label.replace("​", "").replace("\xa0", " ")
        return normalized.strip().lower()


def _parse_int(text: str) -> int | None:
    """Parse an integer value from text.

    Handles spaces and commas/dots as thousands separators.

    Args:
        text: The raw text to parse.

    Returns:
        Parsed integer, or None if parsing fails.
    """
    cleaned = text.replace(" ", "").replace(",", "").replace(".", "")
    try:
        return int(cleaned)
    except ValueError:
        logger.warning("Could not parse int from '{text}'", text=text)
        return None


def _parse_price(text: str) -> Decimal | None:
    """Parse a Decimal price from European-format text.

    Handles formats like '3,00 €' or '1.234,50 €' where comma is
    the decimal separator and dot is the thousands separator.

    Args:
        text: The raw price text.

    Returns:
        Parsed Decimal value, or None if parsing fails.
    """
    cleaned = text.replace("€", "").strip()
    cleaned = cleaned.replace(" ", "")
    cleaned = cleaned.replace(".", "")  # Remove thousands separator first
    if "," in cleaned:
        cleaned = cleaned.replace(",", ".")  # Then convert decimal separator
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        logger.warning("Could not parse price from '{text}'", text=text)
        return None
