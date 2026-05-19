# scripts/scrape_reviews.py
# Scrape Google Play reviews for CBE, BOA, and Dashen Bank
# Run this from your project root: python scripts/scrape_reviews.py

import pandas as pd
import time
import os
import re
from datetime import datetime
from google_play_scraper import app, reviews, Sort

# ── Configuration ───────────────────────────────────────────────────
APPS = [
    {
        "app_id":    "com.combanketh.mobilebanking",
        "bank_name": "Commercial Bank of Ethiopia",
        "app_name":  "CBE Mobile Banking"
    },
    {
        "app_id":    "com.boa.boaMobileBanking",
        "bank_name": "Bank of Abyssinia",
        "app_name":  "BoA Mobile"
    },
    {
        "app_id":    "com.dashen.dashensuperapp",
        "bank_name": "Dashen Bank",
        "app_name":  "Dashen Super App"
    }
]

TARGET_PER_BANK = 500   # scrape more than 400 to be safe
SLEEP_BETWEEN   = 5     # seconds between banks


# ── Helper functions ─────────────────────────────────────────────────
def get_app_info(app_id, bank_name):
    """Fetch and print app metadata before scraping."""
    print(f"\n{'='*55}")
    print(f"  {bank_name}")
    print(f"{'='*55}")
    try:
        info = app(app_id, lang='en', country='et')
        print(f"  App Title    : {info['title']}")
        print(f"  Overall Score: {info['score']:.2f}")
        print(f"  Total Ratings: {info['ratings']:,}")
        print(f"  Installs     : {info['installs']}")
    except Exception as e:
        print(f"  Metadata unavailable: {e}")


def clean_text(text):
    """Collapse whitespace and strip edges."""
    if pd.isna(text):
        return ''
    text = str(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def scrape_bank(app_id, bank_name, app_name, target=500):
    """
    Scrape reviews for one bank in batches until target is reached.
    Uses continuation_token to paginate through results.
    """
    get_app_info(app_id, bank_name)
    print(f"\n  Scraping reviews (target: {target})...")

    all_reviews        = []
    continuation_token = None
    batch_num          = 0

    while len(all_reviews) < target:
        batch_num += 1
        print(f"  Batch {batch_num} — collected so far: {len(all_reviews)}")

        try:
            result, continuation_token = reviews(
                app_id,
                lang='en',
                country='et',            # Ethiopia locale — more relevant reviews
                sort=Sort.NEWEST,        # newest first
                count=200,               # max per batch
                filter_score_with=None,  # all star ratings
                continuation_token=continuation_token
            )
        except Exception as e:
            print(f"  ERROR on batch {batch_num}: {e}")
            print(f"  Trying with country='us'...")
            try:
                result, continuation_token = reviews(
                    app_id,
                    lang='en',
                    country='us',
                    sort=Sort.NEWEST,
                    count=200,
                    filter_score_with=None,
                    continuation_token=continuation_token
                )
            except Exception as e2:
                print(f"  Both locales failed: {e2}. Stopping.")
                break

        if not result:
            print(f"  No more reviews returned. Stopping.")
            break

        for r in result:
            all_reviews.append({
                'review_id': r.get('reviewId', ''),
                'review'   : r.get('content', ''),
                'rating'   : r.get('score', None),
                'date'     : r.get('at', None),
                'bank'     : bank_name,
                'app_name' : app_name,
                'source'   : 'Google Play'
            })

        if continuation_token is None:
            print(f"  Reached end of available reviews.")
            break

        time.sleep(1)

    print(f"  ✓ Collected {len(all_reviews)} reviews for {bank_name}")
    return all_reviews


def scrape_by_rating(app_id, bank_name, app_name, max_per_star=100):
    """
    Fallback: scrape by star rating (MOST_RELEVANT) to maximise coverage.
    Returns list of review dicts.
    """
    all_reviews = []
    for star in [1, 2, 3, 4, 5]:
        print(f"  Scraping {star}★ reviews (fallback)...")
        try:
            result, _ = reviews(
                app_id,
                lang='en',
                country='et',
                sort=Sort.MOST_RELEVANT,
                count=max_per_star,
                filter_score_with=star
            )
            for r in result:
                all_reviews.append({
                    'review_id': r.get('reviewId', ''),
                    'review'   : r.get('content', ''),
                    'rating'   : r.get('score', None),
                    'date'     : r.get('at', None),
                    'bank'     : bank_name,
                    'app_name' : app_name,
                    'source'   : 'Google Play'
                })
            print(f"    Got {len(result)} reviews for {star}★")
        except Exception as e:
            print(f"    {star}★ failed: {e}")
        time.sleep(1.5)   # slightly longer to be gentle
    return all_reviews


def preprocess(df_raw):
    """
    Clean the raw DataFrame and return analysis-ready DataFrame.
    Documents every step with counts.
    """
    df       = df_raw.copy()
    original = len(df)

    print(f"\n{'='*55}")
    print(f"  DATA QUALITY AUDIT")
    print(f"{'='*55}")

    # Problem 1: Missing values
    print(f"\nProblem 1 — Missing Values:")
    for col in df.columns:
        n = df[col].isnull().sum()
        print(f"  {col:<15}: {n} missing" if n > 0 else f"  {col:<15}: OK")

    # Problem 2: Duplicates
    exact_dupes = df.duplicated(subset=['review']).sum()
    id_dupes    = df.duplicated(subset=['review_id']).sum()
    empty       = (df['review'].astype(str).str.strip() == '').sum()
    print(f"\nProblem 2 — Duplicates:")
    print(f"  Exact duplicate reviews : {exact_dupes}")
    print(f"  Duplicate review IDs    : {id_dupes}")
    print(f"  Empty review texts      : {empty}")

    # Problem 3: Date format
    print(f"\nProblem 3 — Date Format:")
    print(f"  Current dtype : {df['date'].dtype}")
    print(f"  Target format : YYYY-MM-DD")

    # ── Fix 1: Drop missing critical fields ──────────────────
    df = df.dropna(subset=['review', 'rating'])

    # ── Fix 2: Remove duplicates ─────────────────────────────
    df = df.drop_duplicates(subset=['review_id'], keep='first')

    # ── Fix 3: Normalize dates to YYYY-MM-DD ─────────────────
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
    df = df.dropna(subset=['date'])

    # ── Fix 4: Clean review text ──────────────────────────────
    df['review'] = df['review'].apply(clean_text)
    df = df[df['review'].str.len() > 0]

    # ── Fix 5: Validate rating range ──────────────────────────
    df = df[(df['rating'] >= 1) & (df['rating'] <= 5)]
    df['rating'] = df['rating'].astype(int)

    # ── Select final 5 required columns ───────────────────────
    df_clean = df[['review', 'rating', 'date', 'bank', 'source']].copy()
    df_clean = df_clean.sort_values('date', ascending=False).reset_index(drop=True)

    # ── Preprocessing report ───────────────────────────────────
    final_count    = len(df_clean)
    removed        = original - final_count
    retention_rate = final_count / original * 100 if original > 0 else 0
    quality        = "EXCELLENT" if retention_rate >= 95 else (
                     "GOOD"      if retention_rate >= 90 else "NEEDS ATTENTION")

    print(f"\n{'='*55}")
    print(f"  PREPROCESSING REPORT")
    print(f"{'='*55}")
    print(f"  Raw reviews collected  : {original:>6}")
    print(f"  Reviews after cleaning : {final_count:>6}")
    print(f"  Reviews removed        : {removed:>6}")
    print(f"  Data retention rate    : {retention_rate:>5.1f}%")
    print(f"  Data quality           : {quality}")
    if final_count > 0:
        print(f"  Date range : {df_clean['date'].min()}  →  {df_clean['date'].max()}")
        print(f"\n  Rating distribution (all banks):")
        for rating in sorted(df_clean['rating'].unique(), reverse=True):
            count = (df_clean['rating'] == rating).sum()
            pct   = count / final_count * 100
            bar   = '█' * (count // 10)
            print(f"    {rating}★ : {count:>4} ({pct:4.1f}%)  {bar}")
        print(f"\n  Reviews per bank:")
        for bank, grp in df_clean.groupby('bank'):
            print(f"    {bank}: {len(grp)}")
    print(f"{'='*55}")

    return df_clean


# ── Main ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target  : {TARGET_PER_BANK} reviews per bank\n")

    # 1. Scrape all banks
    all_data = []
    for i, config in enumerate(APPS):
        bank_data = scrape_bank(
            app_id    = config['app_id'],
            bank_name = config['bank_name'],
            app_name  = config['app_name'],
            target    = TARGET_PER_BANK
        )

        # Fallback if needed
        if len(bank_data) < 400:
            print(f"  ⚠ Only {len(bank_data)} reviews for {config['bank_name']}, trying fallback...")
            extra = scrape_by_rating(
                config['app_id'],
                config['bank_name'],
                config['app_name']
            )
            # Combine and deduplicate by review_id
            existing_ids = {r['review_id'] for r in bank_data}
            for r in extra:
                if r['review_id'] not in existing_ids:
                    bank_data.append(r)
            print(f"  After fallback: {len(bank_data)} reviews for {config['bank_name']}")

        all_data.extend(bank_data)

        if i < len(APPS) - 1:
            print(f"\n  Waiting {SLEEP_BETWEEN}s before next bank...")
            time.sleep(SLEEP_BETWEEN)

    # 2. Build raw DataFrame and save
    df_raw = pd.DataFrame(all_data)
    os.makedirs('data/raw', exist_ok=True)
    df_raw.to_csv('data/raw/reviews_raw.csv', index=False)
    print(f"\n✓ Raw data saved: {len(df_raw)} total rows")

    # 3. Check if any bank is under 400
    print("\nPer-bank count before cleaning:")
    for bank, grp in df_raw.groupby('bank'):
        status = "✓ OK" if len(grp) >= 400 else "⚠ BELOW 400 — document this"
        print(f"  {bank}: {len(grp)} reviews  {status}")

    # 4. Preprocess
    df_clean = preprocess(df_raw)

    # 5. Save clean file
    df_clean.to_csv('data/raw/reviews_clean.csv', index=False)
    print(f"\n✓ Clean data saved: {len(df_clean)} rows → data/raw/reviews_clean.csv")
    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")