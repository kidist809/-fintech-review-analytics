"""Database load utilities: create schema and insert processed reviews.

Uses `DATABASE_URL` environment variable for a PostgreSQL connection. If not
set, falls back to a local SQLite file at `data/reviews.db` for local testing.
"""
import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Date, Float, ForeignKey, Text
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd


def get_engine():
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        print('Using DATABASE_URL from environment')
        return create_engine(db_url)
    else:
        print('DATABASE_URL not set — falling back to sqlite:///data/reviews.db')
        os.makedirs('data', exist_ok=True)
        return create_engine('sqlite:///data/reviews.db')


def create_schema(engine):
    meta = MetaData()
    banks = Table('banks', meta,
                  Column('bank_id', Integer, primary_key=True, autoincrement=True),
                  Column('bank_name', String(255), unique=True, nullable=False),
                  Column('app_name', String(255))
                  )

    reviews = Table('reviews', meta,
                    Column('review_id', Integer, primary_key=True, autoincrement=True),
                    Column('bank_id', Integer, ForeignKey('banks.bank_id')),
                    Column('review_text', Text, nullable=False),
                    Column('rating', Integer, nullable=False),
                    Column('review_date', Date),
                    Column('sentiment_label', String(50)),
                    Column('sentiment_score', Float),
                    Column('identified_theme', String(100)),
                    Column('source', String(100))
                    )
    meta.create_all(engine)
    print('Created schema (if not exists)')
    return banks, reviews


def load_reviews(engine, df: pd.DataFrame):
    conn = engine.connect()
    meta = MetaData(bind=engine)
    banks = Table('banks', meta, autoload_with=engine)
    reviews = Table('reviews', meta, autoload_with=engine)

    # Upsert banks
    bank_name_to_id = {}
    for bank in df['bank'].unique():
        sel = conn.execute(banks.select().where(banks.c.bank_name == bank)).fetchone()
        if sel is None:
            res = conn.execute(banks.insert().values(bank_name=bank, app_name=bank))
            bank_id = res.inserted_primary_key[0]
        else:
            bank_id = sel['bank_id']
        bank_name_to_id[bank] = bank_id

    # Insert reviews (basic dedupe by identical review text + bank)
    inserted = 0
    for _, row in df.iterrows():
        # check exists
        exists = conn.execute(reviews.select().where(
            (reviews.c.review_text == row['review']) & (reviews.c.bank_id == bank_name_to_id[row['bank']])
        )).fetchone()
        if exists:
            continue
        try:
            conn.execute(reviews.insert().values(
                bank_id=bank_name_to_id[row['bank']],
                review_text=row['review'],
                rating=int(row['rating']),
                review_date=pd.to_datetime(row['date']).date() if not pd.isna(row['date']) else None,
                sentiment_label=row.get('sentiment_label'),
                sentiment_score=float(row.get('sentiment_score')) if not pd.isna(row.get('sentiment_score')) else None,
                identified_theme=row.get('identified_theme'),
                source=row.get('source')
            ))
            inserted += 1
        except SQLAlchemyError as e:
            print('Insert failed for one row:', e)

    print(f'Inserted {inserted} new reviews')


def main(processed_csv: str = 'data/processed/reviews_processed.csv'):
    if not os.path.exists(processed_csv):
        raise FileNotFoundError(f'{processed_csv} not found — run processing step first')
    df = pd.read_csv(processed_csv)
    engine = get_engine()
    create_schema(engine)
    load_reviews(engine, df)


if __name__ == '__main__':
    main()
