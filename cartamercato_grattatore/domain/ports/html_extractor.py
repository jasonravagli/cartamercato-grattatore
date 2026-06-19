from abc import ABC, abstractmethod

from overrides import EnforceOverrides

from cartamercato_grattatore.domain.data_models.scraping import CardmarketProductInfo


class BaseHtmlExtractor(ABC, EnforceOverrides):
    """Abstract interface defining HTML extraction functionality."""

    @abstractmethod
    def extract(self, html: str, product_name: str, url: str) -> CardmarketProductInfo:
        """Extract structured product information from raw HTML.

        Args:
            html: The raw HTML source of the product page.
            product_name: The product name from the CSV input.
            url: The product URL that was scraped.

        Returns:
            A CardmarketProductInfo model with extracted data.

        Raises:
            ExtractionError: If extraction fails due to missing
                structural elements.
        """
        pass

    @abstractmethod
    def can_extract(self, html: str) -> bool:
        """Check whether the HTML contains extractable content.

        Args:
            html: The raw HTML source to inspect.

        Returns:
            True if the HTML structure matches expectations, False otherwise.
        """
        pass
