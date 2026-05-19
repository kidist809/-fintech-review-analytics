# fintech-review-analytics

Repository scaffold for fintech review analytics.

## Structure

- `.vscode/`
- `.github/`
- `data/`
- `notebooks/`
- `src/`
- `tests/`
- `scripts/`

## Getting started

Use `requirements.txt` to install dependencies and add project code under `src/`.

## Quick start

1. Create a virtual environment and install dependencies:

	python -m venv .venv
	.venv\Scripts\activate   # Windows
	pip install -r requirements.txt

2. Scrape reviews (writes `data/raw/reviews_raw.csv` and `data/raw/reviews_clean.csv`):

	python scripts/scrape_reviews.py

3. Run sentiment + thematic pipeline (writes `data/processed/reviews_processed.csv`):

	python -m src.sentiment_thematic

4. Load into database (uses `DATABASE_URL` env var or falls back to sqlite):

	python -m src.db_load

Notes:
- Do NOT commit CSVs or database files. `data/` is included in `.gitignore`.
- The transformer sentiment step downloads a model on first run; ensure internet access.

