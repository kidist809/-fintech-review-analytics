import pandas as pd
from sqlalchemy import create_engine
from src import db_load


def test_create_schema_and_insert():
    engine = create_engine('sqlite:///:memory:')
    # create schema
    banks, reviews = db_load.create_schema(engine)
    # prepare small df
    rows = [
        {
            'review': 'Great app, fast transfer',
            'rating': 5,
            'date': '2026-05-01',
            'bank': 'Test Bank',
            'source': 'Google Play',
            'sentiment_label': 'positive',
            'sentiment_score': 0.98,
            'identified_theme': 'Transaction Performance'
        }
    ]
    df = pd.DataFrame(rows)
    # load reviews
    db_load.load_reviews(engine, df)
    # basic verification: counts
    conn = engine.connect()
    res = conn.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]
    assert res >= 1
