# Technologies

- **Python**: 3.14+ (see `.python-version`)
- **Package manager**: `uv` (lockfile: `uv.lock`)
- **Linting/formatting**: Ruff (configured in `pyproject.toml`)
- **Pytest** for testing
- **Loguru** for logging
- **Nodriver** (stealth Chromium, CDP) as the primary web scraper. It runs a real
  browser with a per-run (reset at each launch) profile and passes
  Cloudflare-protected sites
  (Cardmarket) that block headless and Selenium-masked browsers. Selected by
  default via the CLI `--scraper nodriver`.
- **Selenium** — legacy scraping engine, kept as the `--scraper selenium`
  fallback (not supported against Cloudflare-protected Cardmarket).
- **BeautifulSoup** to extract structured product data from scraped HTML
