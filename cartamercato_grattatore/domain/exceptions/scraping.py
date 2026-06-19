class ScrapingError(Exception):
    """Exception raised when a scraping operation fails."""

    pass


class ExtractionError(Exception):
    """Exception raised when HTML data extraction fails."""

    pass
