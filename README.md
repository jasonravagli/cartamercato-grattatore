# Cartamercato Grattatore

Scrapes product information from Cardmarket and publishes it to a Google Spreadsheet.

## How to update the project

From the terminal, move to the project directory:

```
cd path/to/folder
```

Then run:

```
git pull
```

## How to Run

1. From the terminal, move to the project directory:

    ```
    cd path/to/folder
    ```

2. Install [uv](https://docs.astral.sh/uv/), then install dependencies:

   ```bash
   make install
   ```

3. Run the application:

   ```bash
   uv run python -m cartamercato_grattatore
   ```

   Each run creates a `logs/{timestamp}-{uuid}/` directory with logs and session artifacts. See the following section for more arguments

### Useful options

```bash
# CSV with product URLs (default: assets/products.csv)
uv run python -m cartamercato_grattatore --csv-file path/to/products.csv

# Choose scraping engine (nodriver is default and handles Cloudflare)
uv run python -m cartamercato_grattatore --scraper nodriver

# Run on a schedule (app stays alive until interrupted)
uv run python -m cartamercato_grattatore --times "09:00,14:00,20:00"
```

Other flags: `--google-spreadsheet-url`, `--google-credentials-path` (or set `GOOGLE_APPLICATION_CREDENTIALS`), `--headless` (avoid for live scraping — Cardmarket blocks headless browsers).

For development details, see [docs/execution.md](docs/execution.md).